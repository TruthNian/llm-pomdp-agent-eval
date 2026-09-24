"""Boundary checks for the optional native Codex runtime pilot."""
import queue
import unittest

from tools.native_codex_stream import AppServer, action, tool_output


class NativeCodexStreamTests(unittest.TestCase):
    def test_malformed_finish_cannot_handover(self):
        self.assertEqual(action("finish", {"target": "anything"}), {"command": "invalid"})
        self.assertEqual(action("exec", {"target": "pwd", "extra": 1}), {"command": "invalid"})
        self.assertEqual(action("finish", {}), {"command": "finish"})
        observation = {"steps_remaining": 199, "result": {"output": "safe"}, "done": False}
        self.assertEqual(tool_output(observation)["contentItems"][0]["text"],
                         '{"steps_remaining": 199, "result": {"output": "safe"}, "done": false}')

    def test_rpc_preserves_notifications_before_response(self):
        app = object.__new__(AppServer)
        app.counter = 0
        app.backlog = []
        app.messages = queue.Queue()
        sent = []
        app.send = sent.append
        app.messages.put({"method": "item/completed", "params": {"item": {"type": "userMessage"}}})
        app.messages.put({"id": 1, "result": {"thread": {"id": "one"}}})
        self.assertEqual(app.rpc("thread/start", {}, timeout=1), {"thread": {"id": "one"}})
        self.assertEqual(len(sent), 1)
        self.assertEqual(app.next(.01)["method"], "item/completed")


if __name__ == "__main__":
    unittest.main()
