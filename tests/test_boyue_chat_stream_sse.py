import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import unittest

from tools.boyue_chat_stream import native_action
from tools.boyue_chat_stream_sse import exchange


class BoyueChatStreamSseTests(unittest.TestCase):
    def test_stream_reassembles_reasoning_tool_arguments_and_usage(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                events = [
                    {"model": "candidate", "choices": [{"index": 0, "delta": {"role": "assistant", "reasoning_content": "think", "name": "candidate", "audio_content": "", "reasoning_details": [{"format": "MiniMax-response-v1", "id": "rs_1", "index": 0, "text": "first", "type": "reasoning.text"}]}, "finish_reason": None}]},
                    {"model": "candidate", "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call-1", "type": "function", "function": {"name": "exec", "arguments": '{"target":'}}], "reasoning_details": [{"format": "MiniMax-response-v1", "id": "rs_1", "index": 0, "text": " second", "type": "reasoning.text"}]}, "finish_reason": None}]},
                    {"model": "candidate", "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"pwd"}'}}]}, "finish_reason": None}]},
                    {"model": "candidate", "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
                    {"model": "candidate", "choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 4}},
                ]
                body = b"".join(b"data: " + json.dumps(event).encode() + b"\n\n" for event in events) + b"data: [DONE]\n\n"
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
            data = exchange(f"http://127.0.0.1:{server.server_port}/chat/completions", "fixture-key",
                            {"model": "candidate", "messages": [], "stream": False}, audit,
                            timeout=2, byte_limit=10000)
            self.assertIs(requests[0]["stream"], True)
            self.assertEqual(native_action(data, "candidate")[0], {"command": "exec", "target": "pwd"})
            self.assertEqual(data["choices"][0]["message"]["reasoning_content"], "think")
            self.assertEqual(data["choices"][0]["message"]["reasoning_details"][0]["text"], "first second")
            self.assertEqual(data["choices"][0]["message"]["name"], "candidate")
            self.assertEqual(data["usage"]["prompt_tokens"], 3)
            self.assertEqual(audit["event_count"], 5)
            self.assertEqual(audit["outcome"], "response")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
