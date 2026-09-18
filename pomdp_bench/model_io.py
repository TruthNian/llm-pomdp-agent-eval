"""One bounded HTTP action channel; no agent runtime, tools, or response chaining."""
from __future__ import annotations

import copy
import hashlib
import http.client
import json
import math
import os
import socket
import threading
import time
import urllib.parse

MAX_RESPONSE_BYTES = 2_000_000
SYSTEM = ("You are an agent in an interactive environment. Follow the task contract. "
          "Return exactly one JSON action with command and optional target, without commentary or markdown. "
          "The user JSON includes the complete public observation history. No external tools are available.")


class AdapterError(RuntimeError):
    """Only fixed local descriptions and numeric HTTP status, never remote bodies."""

    def __init__(self, message, code="adapter_error"):
        super().__init__(message)
        self.code = code


def strict_json(text):
    def constant(_):
        raise ValueError("Nonfinite numbers are not JSON")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON keys")
            result[key] = value
        return result

    return json.loads(text, parse_constant=constant, object_pairs_hook=pairs)


def request_body(config, request):
    public = json.dumps(request, ensure_ascii=False, allow_nan=False)
    options = copy.deepcopy(config.get("options", {}))
    if config["kind"] == "chat":
        return {"model": config["model"], **options, "stream": False, "n": 1,
                "tools": [], "tool_choice": "none", "messages": [
                    {"role": "system", "content": SYSTEM}, {"role": "user", "content": public}]}
    if "reasoning_effort" in options:
        options["reasoning"] = {"effort": options.pop("reasoning_effort")}
    return {"model": config["model"], **options, "instructions": SYSTEM,
            "input": [{"role": "user", "content": public}],
            "tools": [], "tool_choice": "none", "store": False, "stream": True}


def action_text(data, kind):
    if not isinstance(data, dict) or data.get("error"):
        raise AdapterError("Endpoint returned an error envelope", "protocol_error")
    try:
        if kind == "chat":
            choices = data["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError()
            choice = choices[0]
            message = choice["message"]
            if message.get("tool_calls") not in (None, []) or message.get("function_call") is not None:
                raise AdapterError("Endpoint returned an undeclared tool call", "unexpected_tool")
            if choice.get("finish_reason") != "stop":
                raise AdapterError("Endpoint did not finish one action", "incomplete_response")
            if message.get("role") != "assistant" or message.get("refusal"):
                raise ValueError()
            text = message["content"]
        else:
            if data.get("status") != "completed" or data.get("incomplete_details"):
                raise AdapterError("Endpoint did not complete the response", "incomplete_response")
            messages = []
            for item in data["output"]:
                kind_ = item["type"]
                if kind_ not in ("message", "reasoning"):
                    raise AdapterError("Endpoint returned an undeclared output item", "unexpected_tool")
                if kind_ == "message":
                    if item.get("role") != "assistant" or item.get("status") != "completed":
                        raise ValueError()
                    messages.append(item)
            if len(messages) != 1:
                raise ValueError()
            content = messages[0]["content"]
            if not content or any(x.get("type") != "output_text" for x in content):
                raise ValueError()
            text = "".join(x["text"] for x in content)
        if not isinstance(text, str):
            raise ValueError()
        action = strict_json(text)
        if not isinstance(action, dict):
            raise ValueError()
        return action
    except (KeyError, TypeError, ValueError, AttributeError):
        raise AdapterError("Endpoint did not return one unambiguous JSON action", "protocol_error") from None


class ResponseStream:
    """Inspect events while streaming; commit only a completed response envelope."""

    def __init__(self):
        self.buffer = b""
        self.lines = []
        self.result = None
        self.item_types = {}
        self.completed_items = {}

    def feed(self, chunk, final=False):
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            self.line(line.rstrip(b"\r"))
        if final:
            if self.buffer or self.lines:
                raise AdapterError("Endpoint stream ended inside an event", "incomplete_response")
            if self.result is None:
                raise AdapterError("Endpoint stream ended without completion", "incomplete_response")

    def line(self, line):
        if line:
            if line.startswith(b"data:"):
                self.lines.append(line[5:].lstrip(b" "))
            return
        if not self.lines:
            return
        raw = b"\n".join(self.lines)
        self.lines = []
        if raw == b"[DONE]":
            if self.result is None:
                raise AdapterError("Endpoint stream ended without completion", "incomplete_response")
            return
        event = strict_json(raw)
        if not isinstance(event, dict):
            raise AdapterError("Invalid endpoint stream event", "protocol_error")
        kind = event.get("type", "")
        if kind in ("error", "response.failed", "response.incomplete", "response.cancelled"):
            raise AdapterError("Endpoint stream failed or was incomplete", "incomplete_response")
        allowed = {"response.created", "response.in_progress", "response.queued", "response.completed",
                   "response.output_item.added", "response.output_item.done",
                   "response.content_part.added", "response.content_part.done",
                   "response.output_text.delta", "response.output_text.done", "response.output_text.annotation.added",
                   "response.reasoning_summary_part.added", "response.reasoning_summary_part.done",
                   "response.reasoning_summary_text.delta", "response.reasoning_summary_text.done",
                   "response.reasoning_text.delta", "response.reasoning_text.done"}
        if kind not in allowed:
            raise AdapterError("Endpoint streamed an undeclared event type", "unexpected_tool")
        if self.result is not None:
            raise AdapterError("Endpoint streamed events after completion", "protocol_error")
        if kind in ("response.output_item.added", "response.output_item.done"):
            item = event.get("item", {})
            if item.get("type") not in ("message", "reasoning"):
                raise AdapterError("Endpoint streamed an undeclared output item", "unexpected_tool")
            identity = (item.get("id"), event.get("output_index"))
            if not isinstance(identity[0], str) or not identity[0] or type(identity[1]) is not int or identity[1] < 0:
                raise AdapterError("Endpoint streamed an invalid item identity", "protocol_error")
            if identity in self.item_types and self.item_types[identity] != item["type"]:
                raise AdapterError("Endpoint changed a stream item's type", "protocol_error")
            if (identity in self.completed_items
                    or (kind.endswith(".added") and identity in self.item_types)
                    or any(k != identity and (k[0] == identity[0] or k[1] == identity[1]) for k in self.item_types)):
                raise AdapterError("Endpoint reused a stream item identity", "protocol_error")
            self.item_types[identity] = item["type"]
            if kind.endswith(".done"):
                # Reasoning is never action content and need not be accumulated.
                self.completed_items[identity] = item if item["type"] == "message" else {"type": "reasoning"}
        if kind in ("response.content_part.added", "response.content_part.done"):
            part = event.get("part", {})
            expected = {"output_text": "message", "reasoning_text": "reasoning"}.get(part.get("type"))
            identity = (event.get("item_id"), event.get("output_index"))
            if expected is None or self.item_types.get(identity) != expected:
                raise AdapterError("Endpoint streamed content outside its declared item", "protocol_error")
        for item in event.get("response", {}).get("output", []):
            if item.get("type") not in ("message", "reasoning"):
                raise AdapterError("Endpoint streamed an undeclared output item", "unexpected_tool")
        if kind == "response.completed":
            terminal = event["response"]
            if self.item_types.keys() != self.completed_items.keys():
                raise AdapterError("Endpoint completed with unfinished output items", "incomplete_response")
            closed = [self.completed_items[k] for k in sorted(self.completed_items, key=lambda k: k[1])]
            reported = terminal.get("output")
            if reported is not None and not isinstance(reported, list):
                raise AdapterError("Endpoint returned an invalid output collection", "protocol_error")
            # Native streams close each item and send an empty terminal output.
            # Both item completion and whole-response completion are mandatory.
            if not reported and closed:
                terminal = {**terminal, "output": closed}
            elif reported and closed:
                def messages(items):
                    return [(item.get("role"), item.get("status"), item.get("content"))
                            for item in items if item.get("type") == "message"]
                # Compare completed message content before parsing its action.
                # Invalid action JSON must still reach usage accounting.
                if messages(reported) != messages(closed):
                    raise AdapterError("Endpoint returned conflicting completed actions", "protocol_error")
            self.result = terminal


def exchange(endpoint, key, body, timeout, extra_headers=None, *, streaming=False):
    """No redirects, implicit proxies or retries. Bound reads by one deadline."""
    parsed = urllib.parse.urlsplit(endpoint)
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    deadline = time.monotonic() + timeout

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError()
        return value

    connection = connection_type(parsed.hostname, parsed.port, timeout=remaining())
    live_socket = [None]

    def expire():
        sock = live_socket[0] or connection.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(remaining(), expire)
    timer.daemon = True
    timer.start()
    response = None
    try:
        connection.connect()
        sock = connection.sock
        live_socket[0] = sock
        sock.settimeout(remaining())
        connection.request("POST", parsed.path or "/", body,
                           {"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                            "Accept": "application/json, text/event-stream", **(extra_headers or {})})
        sock.settimeout(remaining())
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise AdapterError(f"Endpoint HTTP status {response.status}", "http_error")
        media = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        # A missing media header uses the format we explicitly requested.
        # Never sniff arbitrary body text or treat a delta as an action.
        stream = ResponseStream() if media == "text/event-stream" or (not media and streaming) else None
        chunks, size = [], 0
        while not response.isclosed():
            sock.settimeout(remaining())
            chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - size))
            remaining()
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise AdapterError("Response exceeds adapter size limit", "response_too_large")
            if stream:
                stream.feed(chunk)
            else:
                chunks.append(chunk)
        if response.length not in (None, 0):
            raise AdapterError("Endpoint body ended before its declared length", "incomplete_response")
        if stream:
            stream.feed(b"", final=True)
            return stream.result
        return strict_json(b"".join(chunks))
    except TimeoutError:
        raise AdapterError("Endpoint request deadline exceeded", "timeout") from None
    except (OSError, http.client.HTTPException):
        if time.monotonic() >= deadline:
            raise AdapterError("Endpoint request deadline exceeded", "timeout") from None
        raise AdapterError("Endpoint transport failed", "transport_error") from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise AdapterError("Endpoint returned malformed JSON or stream data", "protocol_error") from None
    finally:
        timer.cancel()
        if response is not None:
            response.close()
        connection.close()


class HttpAgent:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        self.usage = {"requests": 0, "requests_with_usage": 0, "input_tokens": 0, "output_tokens": 0,
                      "reasoning_tokens": 0, "requests_with_reasoning_usage": 0}
        self.request_audit = []
        self.endpoint = os.environ.get(config["endpoint_env"], "")
        try:
            parsed = urllib.parse.urlsplit(self.endpoint)
            parsed.port  # Validate a malformed port before starting an episode request.
        except ValueError:
            raise AdapterError("Invalid endpoint URL", "configuration_error") from None
        if (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1"))):
            raise AdapterError("Endpoint must be HTTPS (HTTP allowed for loopback)", "configuration_error")
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or any(ord(x) <= 32 for x in self.endpoint)):
            raise AdapterError("Endpoint must not embed credentials, query parameters or fragments", "configuration_error")
        self.key = os.environ.get(config["api_key_env"])
        if not self.key or any(ord(x) < 32 or ord(x) == 127 for x in self.key):
            raise AdapterError("api_key_env is unset or invalid", "configuration_error")
        self.headers = {}
        if config.get("headers_env"):
            try:
                headers = strict_json(os.environ.get(config["headers_env"], ""))
                if (not isinstance(headers, dict) or any(not isinstance(k, str)
                        or not (k.lower().startswith("x-") or k.lower() == "chatgpt-account-id")
                        or not all(c.isascii() and (c.isalnum() or c == "-") for c in k)
                        or not isinstance(v, str) or not v.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in v)
                        for k, v in headers.items()) or len({k.lower() for k in headers}) != len(headers)):
                    raise ValueError()
                self.headers = headers
            except (TypeError, ValueError):
                raise AdapterError("headers_env must contain distinct allowed metadata headers with ASCII values", "configuration_error") from None

    def act(self, request, timeout):
        body = json.dumps(request_body(self.config, request), ensure_ascii=False, allow_nan=False).encode()
        limit = min(timeout, self.config.get("timeout_seconds", 30))
        if not math.isfinite(limit) or limit <= 0:
            raise AdapterError("Endpoint request deadline exceeded", "timeout")
        audit = {"protocol": self.config["kind"], "request_sha256": hashlib.sha256(body).hexdigest(),
                 "declared_tools": [], "tool_choice": "none", "timeout_seconds": limit, "outcome": "in_flight"}
        self.request_audit.append(audit)
        self.usage["requests"] += 1
        try:
            data = exchange(self.endpoint, self.key, body, limit, self.headers,
                            streaming=self.config["kind"] == "responses")
            self.add_usage(data)
            action = action_text(data, self.config["kind"])
            audit["outcome"] = "action"
            # Only record expected model names, not arbitrary provider text.
            audit["reported_model_matches_request"] = data.get("model") == self.config["model"] if data.get("model") else None
            return action
        except AdapterError as exc:
            audit["outcome"] = exc.code
            raise

    def add_usage(self, data):
        usage = data.get("usage") if isinstance(data, dict) else None
        inputs, outputs = ("prompt_tokens", "completion_tokens") if self.config["kind"] == "chat" else ("input_tokens", "output_tokens")
        if isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in (inputs, outputs)):
            self.usage["requests_with_usage"] += 1
            self.usage["input_tokens"] += usage[inputs]
            self.usage["output_tokens"] += usage[outputs]
            details = usage.get(outputs + "_details")
            value = details.get("reasoning_tokens") if isinstance(details, dict) else None
            if type(value) is int and value >= 0:
                self.usage["requests_with_reasoning_usage"] += 1
                self.usage["reasoning_tokens"] += value


# Preserve the public name used by existing integrations.
ChatAgent = HttpAgent
ResponsesAgent = HttpAgent
