"""Wire-level counterexamples for the action-only model channel."""
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from pomdp_bench.agents import validate_agent_version, validate_config
from pomdp_bench.collection import run_suite, resume_suite
from pomdp_bench.evaluation import run_episode
from pomdp_bench.generator import generate, suite
from pomdp_bench.model_io import (AdapterError, HttpAgent, MAX_RESPONSE_BYTES, ResponseStream,
                                 action_text, request_body, strict_json)
from pomdp_bench.reporting import validate_run


def config(kind="responses"):
    return {"name": "wire-fixture", "kind": kind, "model": "test-model", "endpoint_env": "WIRE_ENDPOINT",
            "api_key_env": "WIRE_KEY", "timeout_seconds": 2}


def response(text='{"command":"finish"}'):
    return {"model": "test-model", "status": "completed", "output": [
        {"type": "reasoning", "summary": []},
        {"type": "message", "status": "completed", "role": "assistant",
         "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 12, "output_tokens": 7, "output_tokens_details": {"reasoning_tokens": 4}}}


def chat(text='{"command":"finish"}'):
    return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}


def sse(event):
    return b"data: " + json.dumps(event, ensure_ascii=False).encode() + b"\n\n"


def reasoning_stream(result):
    return b"".join(sse(e) for e in [
        {"type": "response.output_item.added", "output_index": 0,
         "item": {"id": "rs_1", "type": "reasoning"}},
        {"type": "response.content_part.added", "output_index": 0, "item_id": "rs_1",
         "part": {"type": "reasoning_text", "text": ""}},
        {"type": "response.reasoning_text.delta", "output_index": 0, "item_id": "rs_1",
         "delta": 'PRIVATE-REASONING-CANARY {"command":"override"}'},
        {"type": "response.content_part.done", "output_index": 0, "item_id": "rs_1",
         "part": {"type": "reasoning_text", "text": 'PRIVATE-REASONING-CANARY {"command":"override"}'}},
        {"type": "response.output_item.done", "output_index": 0,
         "item": {"id": "rs_1", "type": "reasoning", "summary": []}},
        {"type": "response.output_item.added", "output_index": 1,
         "item": {"id": "msg_1", "type": "message"}},
        {"type": "response.content_part.added", "output_index": 1, "item_id": "msg_1",
         "part": {"type": "output_text", "text": ""}},
        {"type": "response.output_item.done", "output_index": 1,
         "item": {"id": "msg_1", **result["output"][-1]}},
        {"type": "response.completed", "response": result},
    ])


@contextmanager
def endpoint(reply):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((raw, dict(self.headers)))
            try:
                reply(self, json.loads(raw))
            except (OSError, ValueError):
                pass  # A deadline or rejected stream deliberately closes the peer.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        with patch.dict(os.environ, {"WIRE_ENDPOINT": f"http://127.0.0.1:{server.server_port}/responses",
                                     "WIRE_KEY": "fixture-credential-not-a-real-key"}):
            yield received
    finally:
        server.shutdown(); server.server_close(); thread.join()


def send(handler, payload, media="application/json", status=200):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", media)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class EnvelopeTests(unittest.TestCase):
    def test_two_protocols_send_only_explicit_public_input_and_no_tools(self):
        public = {"task": {"task": "public"}, "observation": {}, "history": []}
        for kind in ("chat", "responses"):
            cfg = {**config(kind), "options": {"reasoning_effort": "high"}}
            body = request_body(cfg, public)
            self.assertEqual(body["tools"], [])
            self.assertEqual(body["tool_choice"], "none")
            self.assertNotIn("previous_response_id", body)
            if kind == "responses":
                self.assertFalse(body["store"])
                self.assertEqual(body["reasoning"], {"effort": "high"})
                self.assertEqual(json.loads(body["input"][0]["content"]), public)
            else:
                self.assertEqual(json.loads(body["messages"][1]["content"]), public)

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for raw in ('{"command":"finish","command":"verify"}', '{"x":NaN}', '{"x":{"a":1,"a":2}}'):
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_chat_rejects_tool_calls_even_with_a_valid_action(self):
        for field, value in (("tool_calls", [{"function": {"name": "shell"}}]),
                             ("function_call", {}), ("tool_calls", {})):
            data = chat()
            data["choices"][0]["message"][field] = value
            with self.assertRaises(AdapterError) as result:
                action_text(data, "chat")
            self.assertEqual(result.exception.code, "unexpected_tool")

    def test_chat_rejects_truncation_multiple_choices_refusal_and_wrong_role(self):
        broken = []
        data = chat(); data["choices"][0]["finish_reason"] = "length"; broken.append(data)
        data = chat(); data["choices"] *= 2; broken.append(data)
        data = chat(); data["choices"][0]["message"]["refusal"] = "no"; broken.append(data)
        data = chat(); data["choices"][0]["message"]["role"] = "user"; broken.append(data)
        data = chat(); del data["choices"][0]["finish_reason"]; broken.append(data)
        broken.extend([chat('[]'), chat('{"command":"finish"}{"command":"verify"}')])
        for data in broken:
            with self.subTest(data=data), self.assertRaises(AdapterError):
                action_text(data, "chat")

    def test_responses_rejects_all_nonmessage_nonreasoning_items(self):
        for kind in ("function_call", "image_generation_call", "web_search_call", "mcp_call", "future_tool"):
            data = response(); data["output"].append({"type": kind})
            with self.subTest(kind=kind), self.assertRaises(AdapterError) as result:
                action_text(data, "responses")
            self.assertEqual(result.exception.code, "unexpected_tool")

    def test_responses_rejects_incomplete_ambiguous_and_nontext_output(self):
        broken = []
        for status in ("incomplete", "in_progress", "failed", "cancelled"):
            data = response(); data["status"] = status; broken.append(data)
        data = response(); data["output"].append(copy.deepcopy(data["output"][-1])); broken.append(data)
        data = response(); data["output"][-1]["content"] = [{"type": "refusal"}]; broken.append(data)
        data = response(); data["output"] = []; broken.append(data)
        for data in broken:
            with self.subTest(data=data), self.assertRaises(AdapterError):
                action_text(data, "responses")

    def test_stream_handles_byte_boundaries_crlf_and_utf8(self):
        raw = (b": comment\r\n\r\n" + sse({"type": "response.output_text.delta", "delta": "公开"}) +
               sse({"type": "response.completed", "response": response()}) + b"data: [DONE]\n\n")
        parser = ResponseStream()
        for byte in raw:
            parser.feed(bytes([byte]))
        parser.feed(b"", final=True)
        self.assertEqual(action_text(parser.result, "responses"), {"command": "finish"})

    def test_stream_never_treats_text_delta_or_done_marker_as_completed_action(self):
        for raw in (sse({"type": "response.output_text.delta", "delta": '{"command":"finish"}'}),
                    b"data: [DONE]\n\n", b"data: {\"type\":\"response.completed\"}"):
            with self.assertRaises(AdapterError):
                parser = ResponseStream(); parser.feed(raw); parser.feed(b"", final=True)

    def test_stream_rejects_tool_events_and_error_after_valid_text(self):
        for event in ({"type": "response.output_item.added", "item": {"type": "image_generation_call"}},
                      {"type": "response.function_call_arguments.delta", "delta": "secret"},
                      {"type": "future.provider.event"}, {"type": "error", "message": "secret"}):
            with self.assertRaises(AdapterError) as result:
                parser = ResponseStream()
                parser.feed(sse({"type": "response.output_text.delta", "delta": '{"command":"finish"}'}))
                parser.feed(sse(event))
            self.assertNotIn("secret", str(result.exception))

    def test_stream_rejects_events_after_completion(self):
        parser = ResponseStream()
        parser.feed(sse({"type": "response.completed", "response": response()}))
        with self.assertRaises(AdapterError):
            parser.feed(sse({"type": "response.completed", "response": response()}))

    def test_responses_options_cannot_inject_tools_or_continuation(self):
        for options in ({"tools": []}, {"previous_response_id": "x"}, {"seed": 1},
                        {"stream": False}, {"max_tokens": 40}, {"store": True}):
            with self.assertRaises(ValueError):
                validate_config({**config(), "options": options})
        validate_config({**config(), "options": {"reasoning_effort": "high", "max_output_tokens": 100}})

    def test_new_adapter_cannot_be_labeled_as_an_old_framework(self):
        for version in ("2.0.0", "2.1.0", "2.2.0"):
            with self.assertRaises(ValueError):
                validate_agent_version(config(), version)
        validate_agent_version(config(), "2.3.0")

    def test_stream_checks_items_inside_response_envelopes(self):
        raw = sse({"type": "response.created", "response": {"output": [{"type": "function_call"}]}})
        with self.assertRaises(AdapterError):
            ResponseStream().feed(raw)

    def test_reasoning_content_parts_are_ignored_not_executed(self):
        parser = ResponseStream()
        parser.feed(reasoning_stream(response('{"command":"verify"}')), final=True)
        self.assertEqual(action_text(parser.result, "responses"), {"command": "verify"})

    def test_content_parts_must_belong_to_the_declared_item_type(self):
        for item_id, index, part in (("missing", 0, "reasoning_text"), ("rs_1", 1, "reasoning_text"),
                                     ("rs_1", 0, "output_text"), ("msg_1", 1, "reasoning_text"),
                                     ("msg_1", 1, "refusal"), ("msg_1", 1, "function_call")):
            parser = ResponseStream()
            for ident, item_type, output_index in (("rs_1", "reasoning", 0), ("msg_1", "message", 1)):
                parser.feed(sse({"type": "response.output_item.added", "output_index": output_index,
                                 "item": {"id": ident, "type": item_type}}))
            with self.subTest(item_id=item_id, index=index, part=part), self.assertRaises(AdapterError):
                parser.feed(sse({"type": "response.content_part.added", "item_id": item_id,
                                 "output_index": index, "part": {"type": part}}))

    def test_reasoning_support_does_not_permit_tool_events_or_type_changes(self):
        prefix = sse({"type": "response.output_item.added", "output_index": 0,
                      "item": {"id": "rs_1", "type": "reasoning"}})
        for item_type in ("function_call", "image_generation_call", "message"):
            with self.subTest(item_type=item_type), self.assertRaises(AdapterError):
                parser = ResponseStream(); parser.feed(prefix)
                parser.feed(sse({"type": "response.output_item.done", "output_index": 0,
                                 "item": {"id": "rs_1", "type": item_type}}))

    def test_reasoning_only_and_reasoning_inside_final_message_are_not_actions(self):
        data = response(); data["output"] = data["output"][:1]
        with self.assertRaises(AdapterError):
            action_text(data, "responses")
        data = response()
        data["output"][-1]["content"] = [{"type": "reasoning_text", "text": '{"command":"finish"}'}]
        with self.assertRaises(AdapterError):
            action_text(data, "responses")

    def test_closed_items_and_empty_terminal_output_form_one_completed_action(self):
        for empty in ({}, {"output": []}):
            raw = reasoning_stream(response()).split(sse({"type": "response.completed", "response": response()}))[0]
            terminal = {"status": "completed", "usage": {"input_tokens": 4, "output_tokens": 2}, **empty}
            parser = ResponseStream()
            parser.feed(raw + sse({"type": "response.completed", "response": terminal}), final=True)
            self.assertEqual(action_text(parser.result, "responses"), {"command": "finish"})
            self.assertEqual(parser.result["usage"], terminal["usage"])
            self.assertNotIn("PRIVATE-REASONING-CANARY", json.dumps(list(parser.completed_items.values())))

    def test_closed_item_without_whole_completion_does_not_produce_action(self):
        raw = sse({"type": "response.output_item.done", "output_index": 0,
                   "item": {"id": "msg_1", **response()["output"][-1]}})
        parser = ResponseStream(); parser.feed(raw)
        with self.assertRaises(AdapterError):
            parser.feed(b"", final=True)

    def test_completion_cannot_hide_unclosed_items_or_conflicting_action(self):
        parser = ResponseStream()
        parser.feed(sse({"type": "response.output_item.added", "output_index": 0,
                         "item": {"id": "msg_1", "type": "message"}}))
        with self.assertRaises(AdapterError):
            parser.feed(sse({"type": "response.completed", "response": response()}))
        parser = ResponseStream()
        parser.feed(sse({"type": "response.output_item.done", "output_index": 0,
                         "item": {"id": "msg_1", **response()["output"][-1]}}))
        with self.assertRaises(AdapterError):
            parser.feed(sse({"type": "response.completed", "response": response('{"command":"verify"}')}))

    def test_stream_rejects_reused_item_identity_and_duplicate_done(self):
        for item_id, index in (("msg_1", 0), ("msg_1", 1), ("msg_2", 0)):
            parser = ResponseStream()
            parser.feed(sse({"type": "response.output_item.done", "output_index": 0,
                             "item": {"id": "msg_1", **response()["output"][-1]}}))
            with self.subTest(item_id=item_id, index=index), self.assertRaises(AdapterError):
                parser.feed(sse({"type": "response.output_item.done", "output_index": index,
                                 "item": {"id": item_id, **response()["output"][-1]}}))
class TransportTests(unittest.TestCase):
    def test_response_byte_limits_are_declared_bounded_and_versioned(self):
        for value in (None, True, 0, -1, 2.5, "3000000", 64_000_001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_config({**config(), "max_response_bytes": value})
        for value in (1, 64_000_000):
            validate_config({**config(), "max_response_bytes": value})
        with self.assertRaises(ValueError):
            validate_config({"name": "ref", "kind": "reference", "max_response_bytes": 10})
        declared = {**config(), "max_response_bytes": 3_000_000}
        validate_agent_version(declared, "2.5.2")
        with self.assertRaises(ValueError):
            validate_agent_version(declared, "2.5.1")
        for kind in ("chat", "responses"):
            self.assertEqual(request_body(config(kind), {}),
                             request_body({**config(kind), "max_response_bytes": 3_000_000}, {}))

    def test_long_reasoning_stream_needs_explicit_limit_and_stays_bounded(self):
        opening = sse({"type": "response.output_item.added", "output_index": 0,
                       "item": {"id": "rs_1", "type": "reasoning"}})
        delta = sse({"type": "response.reasoning_text.delta", "output_index": 0,
                     "item_id": "rs_1", "delta": "PRIVATE-LONG-REASONING-CANARY" + "x" * 4096})
        raw = reasoning_stream(response()).replace(opening, opening + delta * 512, 1)
        self.assertGreater(len(raw), MAX_RESPONSE_BYTES)
        with endpoint(lambda h, _: send(h, raw, "text/event-stream")) as received:
            for limit in (None, len(raw) - 1, len(raw)):
                cfg = config() if limit is None else {**config(), "max_response_bytes": limit}
                agent = HttpAgent(cfg)
                if limit == len(raw):
                    self.assertEqual(agent.act({}, 2), {"command": "finish"})
                    self.assertEqual(agent.usage["requests_with_usage"], 1)
                else:
                    with self.assertRaises(AdapterError) as result:
                        agent.act({}, 2)
                    self.assertEqual(result.exception.code, "response_too_large")
                    self.assertEqual(agent.usage["requests_with_usage"], 0)
                self.assertEqual(agent.request_audit[0]["max_response_bytes"], limit or MAX_RESPONSE_BYTES)
                self.assertNotIn("PRIVATE-LONG-REASONING-CANARY", json.dumps(agent.request_audit))
            self.assertEqual(len(received), 3)

    def test_configured_limit_also_bounds_nonstreaming_chat_exactly(self):
        raw = json.dumps(chat()).encode() + b" " * 2048
        with endpoint(lambda h, _: send(h, raw)):
            for limit in (len(raw) - 1, len(raw)):
                agent = HttpAgent({**config("chat"), "max_response_bytes": limit})
                if limit == len(raw):
                    self.assertEqual(agent.act({}, 2), {"command": "finish"})
                else:
                    with self.assertRaises(AdapterError) as result:
                        agent.act({}, 2)
                    self.assertEqual(result.exception.code, "response_too_large")

    def test_responses_fixture_completes_and_replays_multiturn_matrix(self):
        from pomdp_bench.agents import ScriptedAgent
        scripted = ScriptedAgent("reference", 0)

        def reply(handler, body):
            public = json.loads(body["input"][0]["content"])
            result = response(json.dumps(scripted.act(public, 10)))
            result["output"][0]["summary"] = [{"type": "summary_text", "text": "PRIVATE-REASONING-CANARY"}]
            send(handler, reasoning_stream(result), "text/event-stream")

        with endpoint(reply) as received, tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            report = run_suite(suite([21]), [{**config(), "max_response_bytes": 3_000_000}], ["open"], 1, out)
            self.assertEqual(report["overall"][0]["successes"], 2)
            _, records = validate_run(out)
            count = len(received)
            resume_suite(out)
            self.assertEqual(len(received), count)
            audits = [a for r in records for a in r["request_audit"]]
            self.assertTrue(all(r["agent"]["max_response_bytes"] == 3_000_000 for r in records))
            self.assertTrue(all(a["max_response_bytes"] == 3_000_000 for a in audits))
            self.assertCountEqual([a["request_sha256"] for a in audits], [hashlib.sha256(raw).hexdigest() for raw, _ in received])
            self.assertTrue(all(a["declared_tools"] == [] and a["tool_choice"] == "none" for a in audits))
            self.assertTrue(all(json.loads(raw)["tools"] == [] for raw, _ in received))
            self.assertEqual(sum(r["usage"]["reasoning_tokens"] for r in records), count * 4)
            saved = json.dumps(records)
            for private in ("PRIVATE-REASONING-CANARY", "fixture-credential-not-a-real-key"):
                self.assertNotIn(private, saved)

    def test_http_error_is_sanitized_and_never_retried(self):
        with endpoint(lambda h, _: send(h, {"error": "PRIVATE-ERROR-CANARY"}, status=502)) as received:
            record = run_episode(generate(0), config(), "open", 0)
        self.assertEqual(len(received), 1)
        self.assertEqual(record["grade"]["steps"], 0)
        self.assertEqual(record["request_audit"][0]["outcome"], "http_error")
        self.assertEqual(record["usage"]["requests_with_usage"], 0)
        self.assertNotIn("PRIVATE-ERROR-CANARY", json.dumps(record))

    def test_tool_stream_never_applies_valid_text_prefix(self):
        raw = sse({"type": "response.output_text.delta", "delta": '{"command":"finish"}'})
        raw += sse({"type": "response.output_item.added", "item": {"type": "image_generation_call"}})
        with endpoint(lambda h, _: send(h, raw, "text/event-stream")):
            record = run_episode(generate(0), config(), "open", 0)
        self.assertEqual(record["events"], [])
        self.assertEqual(record["request_audit"][0]["outcome"], "unexpected_tool")

    def test_failed_json_action_keeps_reported_usage(self):
        with endpoint(lambda h, _: send(h, response("not json"))):
            record = run_episode(generate(0), config(), "open", 0)
        self.assertEqual(record["request_audit"][0]["outcome"], "protocol_error")
        self.assertEqual(record["usage"]["requests_with_usage"], 1)
        self.assertEqual(record["usage"]["output_tokens"], 7)

    def test_failed_stream_action_keeps_reported_usage(self):
        raw = reasoning_stream(response("not json"))
        with endpoint(lambda h, _: send(h, raw, "text/event-stream")):
            record = run_episode(generate(0), config(), "open", 0)
        self.assertEqual(record["events"], [])
        self.assertEqual(record["request_audit"][0]["outcome"], "protocol_error")
        self.assertEqual(record["usage"]["requests_with_usage"], 1)
        self.assertEqual(record["usage"]["output_tokens"], 7)

    def test_redirect_is_not_followed_or_given_credentials(self):
        with endpoint(lambda h, _: send(h, response())) as target:
            location = os.environ["WIRE_ENDPOINT"]
            def redirect(h, _):
                h.send_response(307); h.send_header("Location", location); h.end_headers()
            with endpoint(redirect) as source:
                with self.assertRaises(AdapterError):
                    HttpAgent(config()).act({}, 2)
            self.assertEqual(len(source), 1)
            self.assertEqual(target, [])

    def test_slow_body_cannot_keep_resetting_deadline(self):
        def drip(h, _):
            h.send_response(200); h.send_header("Content-Type", "application/json"); h.end_headers()
            for byte in json.dumps(response()).encode():
                h.wfile.write(bytes([byte])); h.wfile.flush(); time.sleep(.03)
        with endpoint(drip):
            started = time.monotonic()
            with self.assertRaises(AdapterError) as result:
                HttpAgent(config()).act({}, .18)
            self.assertEqual(result.exception.code, "timeout")
            self.assertLess(time.monotonic() - started, 1.5)

    def test_slow_headers_cannot_keep_resetting_deadline(self):
        def drip(h, _):
            for byte in b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n":
                h.wfile.write(bytes([byte])); h.wfile.flush(); time.sleep(.03)
        with endpoint(drip):
            with self.assertRaises(AdapterError) as result:
                HttpAgent(config()).act({}, .18)
            self.assertEqual(result.exception.code, "timeout")

    def test_response_size_limit_counts_stream_bytes(self):
        with endpoint(lambda h, _: send(h, b":" + b"x" * MAX_RESPONSE_BYTES + b"\n\n", "text/event-stream")):
            with self.assertRaises(AdapterError) as result:
                HttpAgent(config()).act({}, 2)
        self.assertEqual(result.exception.code, "response_too_large")

    def test_valid_json_prefix_does_not_hide_a_truncated_http_body(self):
        def truncated(h, _):
            raw = json.dumps(response()).encode()
            h.send_response(200); h.send_header("Content-Length", str(len(raw) + 100)); h.end_headers()
            h.wfile.write(raw)
        with endpoint(truncated):
            with self.assertRaises(AdapterError) as result:
                HttpAgent(config()).act({}, 2)
        self.assertEqual(result.exception.code, "incomplete_response")

    def test_extra_headers_are_environment_only_and_cannot_replace_auth(self):
        for headers in ({"Authorization": "bad"}, {"Host": "bad"}, {"X-A": "bad\r\nX-B: value"},
                        {"X-A": "1", "x-a": "2"}):
            with endpoint(lambda h, _: send(h, response())), patch.dict(os.environ, {"WIRE_HEADERS": json.dumps(headers)}):
                with self.assertRaises(AdapterError):
                    HttpAgent({**config(), "headers_env": "WIRE_HEADERS"})
        with endpoint(lambda h, _: send(h, response())) as received:
            with patch.dict(os.environ, {"WIRE_HEADERS": '{"X-Exact-Route":"1"}'}):
                agent = HttpAgent({**config(), "headers_env": "WIRE_HEADERS"})
                agent.act({}, 2)
            self.assertEqual(received[0][1]["X-Exact-Route"], "1")
            self.assertNotIn("fixture-credential-not-a-real-key", json.dumps(agent.request_audit))

    def test_missing_content_type_uses_requested_stream_format(self):
        def reply(h, _):
            raw = reasoning_stream(response())
            h.send_response(200); h.send_header("Content-Length", str(len(raw))); h.end_headers()
            # Break the SSE prefix across reads: no body sniffing is necessary.
            h.wfile.write(raw[:1]); h.wfile.flush(); h.wfile.write(raw[1:])
        with endpoint(reply):
            self.assertEqual(HttpAgent(config()).act({}, 2), {"command": "finish"})

    def test_headerless_unfinished_stream_cannot_become_a_json_action(self):
        for raw in (b'{"command":"finish"}', sse({"type": "response.output_text.delta",
                                                "delta": '{"command":"finish"}'})):
            def reply(h, _, payload=raw):
                h.send_response(200); h.send_header("Content-Length", str(len(payload))); h.end_headers()
                h.wfile.write(payload)
            with endpoint(reply), self.assertRaises(AdapterError):
                HttpAgent(config()).act({}, 2)

    def test_account_selector_is_explicit_environment_only_metadata(self):
        with endpoint(lambda h, _: send(h, response())) as received:
            with patch.dict(os.environ, {"WIRE_HEADERS": '{"ChatGPT-Account-Id":"PRIVATE-ACCOUNT-CANARY"}'}):
                agent = HttpAgent({**config(), "headers_env": "WIRE_HEADERS"})
                agent.act({}, 2)
            self.assertEqual(received[0][1]["ChatGPT-Account-Id"], "PRIVATE-ACCOUNT-CANARY")
            self.assertNotIn("PRIVATE-ACCOUNT-CANARY", json.dumps(agent.request_audit))


if __name__ == "__main__":
    unittest.main()
