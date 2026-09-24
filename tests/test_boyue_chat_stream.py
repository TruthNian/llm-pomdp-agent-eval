import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from tools.boyue_chat_stream import exchange, native_action, update_usage


class BoyueChatStreamTests(unittest.TestCase):
    def test_tool_call_and_reasoning_survive_continuation(self):
        data = {"model": "candidate", "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None, "reasoning_content": "opaque thought",
            "tool_calls": [{"id": "call_1", "type": "function", "function": {
                "name": "exec", "arguments": '{"target":"pwd"}'}}]}}]}
        action, message, audit = native_action(data, "candidate")
        self.assertEqual(action, {"command": "exec", "target": "pwd"})
        self.assertEqual(message["content"], "")
        self.assertEqual(message["reasoning_content"], "opaque thought")
        self.assertEqual(audit["tool_name"], "exec")
        self.assertIsNone(data["choices"][0]["message"]["content"])

    def test_no_tool_is_agent_stop_and_wrong_model_is_rejected(self):
        data = {"model": "candidate", "choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": "done"}}]}
        self.assertIsNone(native_action(data, "candidate")[0])
        with self.assertRaisesRegex(ValueError, "returned_model_mismatch"):
            native_action(data, "other")

    def test_usage_does_not_invent_missing_reasoning_counts(self):
        total = {"reports": 0, "input_tokens": 0, "output_tokens": 0,
                 "reasoning_reports": 0, "reasoning_tokens": 0}
        update_usage(total, {"prompt_tokens": 4, "completion_tokens": 3})
        self.assertEqual(total, {"reports": 1, "input_tokens": 4, "output_tokens": 3,
                                 "reasoning_reports": 0, "reasoning_tokens": 0})

    def test_transport_success_and_failure_are_audited_without_provider_bodies(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                status = 503 if self.path.endswith("fail") else 200
                body = b'{"model":"candidate","choices":[]}' if status == 200 else b'{"secret":"do not publish"}'
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            audit = {}
            response = exchange(base + "/ok", "fixture-key", {"model": "candidate"}, audit,
                                timeout=2, byte_limit=1000)
            self.assertEqual(response["model"], "candidate")
            self.assertEqual(audit["outcome"], "response")
            failed = {}
            with self.assertRaisesRegex(RuntimeError, "http_error"):
                exchange(base + "/fail", "fixture-key", {"model": "candidate"}, failed,
                         timeout=2, byte_limit=1000)
            self.assertEqual(failed["http_status"], 503)
            self.assertNotIn("secret", str(failed))
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
