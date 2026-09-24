import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import unittest
from unittest.mock import patch
import urllib.error

from tools.boyue_chat_stream_v2 import exchange as routed_exchange, options_for
from tools.boyue_chat_stream_sse_v2 import exchange as sse_exchange


class BoyueRetestAdapterTests(unittest.TestCase):
    def test_completed_choice_without_done_and_extra_delta_is_usable(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                chunks = [
                    {"model": "candidate", "choices": [{"index": 0, "delta": {
                        "role": "assistant", "metadata": {"ignored": True},
                        "tool_calls": [{"index": 0, "id": "call-1", "type": "function",
                                        "function": {"name": "exec", "arguments": '{"target":"pwd"}'}}]},
                        "finish_reason": None}]},
                    {"model": "candidate", "choices": [{"index": 0, "delta": {},
                        "finish_reason": "tool_calls"}]},
                ]
                body = b"".join(b"data: " + json.dumps(item).encode() + b"\n\n" for item in chunks)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            audit = {}
            result = sse_exchange(f"http://127.0.0.1:{server.server_port}/", "fixture-key",
                                  {"model": "candidate", "messages": []}, audit,
                                  timeout=2, byte_limit=10000)
            self.assertEqual(result["choices"][0]["message"]["tool_calls"][0]["id"], "call-1")
            self.assertTrue(audit["terminal_without_done"])
            self.assertEqual(audit["unknown_delta_keys"], ["metadata"])
            self.assertEqual(audit["finish_reason_seen"], "tool_calls")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_missing_finish_reason_stays_nonexecutable_with_precise_audit(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                body = (b'data: {"model":"candidate","choices":[{"index":0,'
                        b'"delta":{"content":"partial"},"finish_reason":null}]}\n\n')
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            audit = {}
            with self.assertRaisesRegex(ValueError, "incomplete_sse"):
                sse_exchange(f"http://127.0.0.1:{server.server_port}/", "fixture-key",
                             {"model": "candidate", "messages": []}, audit,
                             timeout=2, byte_limit=10000)
            self.assertFalse(audit["done_seen"])
            self.assertIsNone(audit["finish_reason_seen"])
            self.assertTrue(audit["model_seen"])
            self.assertEqual(audit["events_seen"], 1)
            self.assertEqual(audit["http_status"], 200)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_transport_failure_records_types_without_exception_text(self):
        audit = {}
        with patch("tools.boyue_chat_stream_sse_v2.urllib.request.urlopen",
                   side_effect=urllib.error.URLError(ConnectionResetError(10054, "secret"))):
            with self.assertRaisesRegex(RuntimeError, "transport_error"):
                sse_exchange("https://example.test/", "fixture-key", {"model": "candidate"},
                             audit, timeout=2, byte_limit=1000)
        self.assertEqual(audit["exception_type"], "URLError")
        self.assertEqual(audit["reason_type"], "ConnectionResetError")
        self.assertEqual(audit["reason_errno"], 10054)
        self.assertNotIn("secret", str(audit))

    def test_retry_is_bounded_and_all_wire_attempts_remain_visible(self):
        response = {"model": "candidate", "choices": [{"finish_reason": "tool_calls",
            "message": {"role": "assistant", "tool_calls": [{"id": "c1", "function": {"name": "exec"}}]}}]}
        def flaky(*args, **kwargs):
            audit = args[3]
            if send.call_count == 1:
                audit.update(outcome="transport_error", exception_type="URLError")
                raise RuntimeError("transport_error")
            audit.update(outcome="response", event_count=2)
            return response
        with patch("tools.boyue_chat_stream_v2.sse.exchange", side_effect=flaky) as send:
            audit = {}
            result = routed_exchange("https://example.test/", "fixture-key",
                                     {"model": "candidate"}, audit, timeout=3,
                                     byte_limit=1000, options={"parallel_tool_calls": False},
                                     max_attempts=2)
        self.assertIs(result, response)
        self.assertEqual(len(audit["wire_attempts"]), 2)
        self.assertEqual(audit["wire_attempts"][0]["error"], "RuntimeError:transport_error")
        self.assertEqual(audit["call_count"], 1)
        self.assertEqual(audit["outcome"], "response")
        self.assertNotIn("error", audit)

    def test_frozen_options_require_serial_tools(self):
        plan = {"models": ["candidate"], "transport": {"stream": True},
                "interface": {"request_options_by_model": {
                    "candidate": {"parallel_tool_calls": False}}}}
        self.assertEqual(options_for(plan, "candidate"), {"parallel_tool_calls": False})
        plan["interface"]["request_options_by_model"]["candidate"] = {}
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            options_for(plan, "candidate")


if __name__ == "__main__":
    unittest.main()
