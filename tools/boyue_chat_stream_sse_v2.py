"""Versioned SSE transport for Boyue retests; original scored code stays frozen."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from pomdp_bench.model_io import strict_json
from tools import boyue_chat_stream as core


def transport_diagnostic(exc: BaseException) -> dict:
    """Record failure shape without URLs, headers, credentials or response text."""
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    result = {"exception_type": type(exc).__name__, "reason_type": type(reason).__name__}
    errno = getattr(reason, "errno", None)
    if isinstance(errno, int):
        result["reason_errno"] = errno
    return result


def exchange(url: str, key: str, payload: dict, audit: dict, *, timeout: float, byte_limit: int) -> dict:
    wire = {**payload, "stream": True}
    body = json.dumps(wire, ensure_ascii=False, allow_nan=False).encode()
    request = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "text/event-stream"})
    audit.update(request_sha256=core.sha256(body), request_bytes=len(body), outcome="in_flight")
    started = time.monotonic()
    raw_sha = hashlib.sha256()
    raw_bytes = 0
    first_event = None
    event_count = 0
    unknown_delta_keys: set[str] = set()
    model = None
    usage = None
    finish_reason = None
    message = {"role": "assistant", "content": ""}
    calls: dict[int, dict] = {}
    reasoning_details: dict[int, dict] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            audit["http_status"] = response.status
            media = response.headers.get_content_type()
            if media != "text/event-stream":
                raise ValueError("unexpected_content_type")
            done = False
            for line in response:
                if time.monotonic() - started > timeout:
                    raise TimeoutError()
                raw_sha.update(line)
                raw_bytes += len(line)
                if raw_bytes > byte_limit:
                    raise ValueError("response_too_large")
                if not line.startswith(b"data:"):
                    continue
                value = line[5:].strip()
                if value == b"[DONE]":
                    done = True
                    break
                event = strict_json(value.decode("utf-8"))
                if not isinstance(event, dict):
                    raise ValueError("invalid_sse_event")
                event_count += 1
                if first_event is None:
                    first_event = round(time.monotonic() - started, 6)
                if event.get("model"):
                    if model is not None and model != event["model"]:
                        raise ValueError("changing_model_label")
                    model = event["model"]
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                for choice in event.get("choices", []):
                    if choice.get("index") not in (0, None):
                        raise ValueError("multiple_choices")
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
                    delta = choice.get("delta") or {}
                    if not isinstance(delta, dict):
                        raise ValueError("unexpected_delta")
                    unknown_delta_keys.update(set(delta) - {"role", "content", "reasoning_content",
                                                               "tool_calls", "name", "audio_content",
                                                               "reasoning_details"})
                    if delta.get("role") not in (None, "assistant"):
                        raise ValueError("wrong_delta_role")
                    for field in ("content", "reasoning_content"):
                        fragment = delta.get(field)
                        if fragment is not None:
                            if not isinstance(fragment, str):
                                raise ValueError("nontext_delta")
                            message[field] = message.get(field, "") + fragment
                    if delta.get("name") is not None:
                        if not isinstance(delta["name"], str) or ("name" in message and message["name"] != delta["name"]):
                            raise ValueError("invalid_message_name")
                        message["name"] = delta["name"]
                    if delta.get("audio_content") is not None:
                        if not isinstance(delta["audio_content"], str):
                            raise ValueError("invalid_audio_content")
                        message["audio_content"] = message.get("audio_content", "") + delta["audio_content"]
                    for detail in delta.get("reasoning_details") or []:
                        if not isinstance(detail, dict) or set(detail) != {"format", "id", "index", "text", "type"}:
                            raise ValueError("invalid_reasoning_detail")
                        index = detail["index"]
                        if type(index) is not int or index < 0 or not isinstance(detail["text"], str):
                            raise ValueError("invalid_reasoning_fragment")
                        existing = reasoning_details.get(index)
                        if existing is None:
                            reasoning_details[index] = dict(detail)
                        else:
                            if any(existing[key] != detail[key] for key in ("format", "id", "index", "type")):
                                raise ValueError("changed_reasoning_detail")
                            existing["text"] += detail["text"]
                    for fragment in delta.get("tool_calls") or []:
                        index = fragment.get("index")
                        if type(index) is not int or index < 0:
                            raise ValueError("invalid_tool_index")
                        call = calls.setdefault(index, {"id": "", "type": "function",
                                                        "function": {"name": "", "arguments": ""}})
                        for field in ("id", "type"):
                            if fragment.get(field):
                                call[field] = fragment[field]
                        function = fragment.get("function") or {}
                        if function.get("name"):
                            call["function"]["name"] = function["name"]
                        if function.get("arguments"):
                            call["function"]["arguments"] += function["arguments"]
        # A final choice is usable after EOF even if the gateway omits [DONE].
        # Without a finish reason, a partial tool argument could be executed.
        if not finish_reason or not model:
            raise ValueError("incomplete_sse")
        if calls:
            message["tool_calls"] = [calls[index] for index in sorted(calls)]
        if reasoning_details:
            message["reasoning_details"] = [reasoning_details[index] for index in sorted(reasoning_details)]
        audit.update(response_sha256=raw_sha.hexdigest(), response_bytes=raw_bytes,
                     first_event_seconds=first_event, event_count=event_count,
                     terminal_without_done=not done, outcome="response")
        return {"model": model, "choices": [{"index": 0, "finish_reason": finish_reason,
                                               "message": message}], "usage": usage}
    except urllib.error.HTTPError as exc:
        audit.update(http_status=exc.code, outcome="http_error", **transport_diagnostic(exc))
        raise RuntimeError("http_error") from None
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        audit.update(transport_diagnostic(exc))
        audit["outcome"] = "timeout" if isinstance(exc, TimeoutError) else "transport_error"
        raise RuntimeError(audit["outcome"]) from None
    finally:
        audit["elapsed_seconds"] = round(time.monotonic() - started, 6)
        audit["events_seen"] = event_count
        audit["first_event_seconds"] = first_event
        audit["response_bytes_seen"] = raw_bytes
        audit["response_sha256_seen"] = raw_sha.hexdigest()
        audit["done_seen"] = done if "done" in locals() else False
        audit["finish_reason_seen"] = finish_reason
        audit["model_seen"] = model is not None
        audit["tool_calls_seen"] = len(calls)
        audit["unknown_delta_keys"] = sorted(unknown_delta_keys)


def run(plan_path: Path, model: str, output: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["transport"]["stream"] is not True:
        raise ValueError("SSE follow-up requires a frozen streaming plan")
    original = core.exchange
    core.exchange = exchange
    try:
        return core.run(plan_path, model, output)
    finally:
        core.exchange = original


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--plan", required=True, type=Path)
    command.add_argument("--model", required=True)
    command.add_argument("--out", required=True, type=Path)
    command.add_argument("--runtime-config", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(core.verify(args.record), ensure_ascii=False))
        return
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    result = run(args.plan, args.model, args.out)
    print(json.dumps({"model": args.model, "grade": result["grade"], "error": result["error"],
                      "usage": result["usage"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
