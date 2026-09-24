import unittest
from unittest.mock import patch

from tools.boyue_chat_stream_sse_qwen import exchange


class QwenRouteTests(unittest.TestCase):
    def test_declared_model_and_effort_are_sent(self):
        with patch("tools.boyue_chat_stream_sse_qwen.sse.exchange", return_value={}) as send:
            exchange("https://example.test", "key", {"model": "qwen3.8-max", "messages": []}, {},
                     timeout=2, byte_limit=100)
        self.assertEqual(send.call_args.args[2]["reasoning_effort"], "medium")
        with self.assertRaisesRegex(ValueError, "model changed"):
            exchange("https://example.test", "key", {"model": "other"}, {},
                     timeout=2, byte_limit=100)


if __name__ == "__main__":
    unittest.main()
