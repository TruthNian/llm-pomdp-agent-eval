import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pomdp_bench import __version__
from pomdp_bench.generator import digest
from tools.boyue_chat_stream_v3 import actions_from_response, run


def response(*calls):
    return {"model": "candidate", "choices": [{"finish_reason": "tool_calls", "message": {
        "role": "assistant", "content": None, "reasoning_content": "opaque",
        "tool_calls": [{"id": identifier, "type": "function", "function": {
            "name": name, "arguments": json.dumps(arguments)}}
            for identifier, name, arguments in calls]}}]}


class BoyueBatchToolTests(unittest.TestCase):
    def test_two_exec_calls_are_accepted_with_distinct_ids_and_reasoning(self):
        actions, message = actions_from_response(response(("c1", "exec", {"target": "pwd"}),
                                                        ("c2", "exec", {"target": "ls"})), "candidate")
        self.assertEqual(actions, [({"command": "exec", "target": "pwd"}, "c1"),
                                   ({"command": "exec", "target": "ls"}, "c2")])
        self.assertEqual(message["reasoning_content"], "opaque")
        self.assertEqual(message["content"], "")

    def test_ambiguous_finish_and_duplicate_ids_are_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "finish_not_last"):
            actions_from_response(response(("c1", "finish", {}),
                                           ("c2", "exec", {"target": "pwd"})), "candidate")
        with self.assertRaisesRegex(ValueError, "invalid_tool_call_id"):
            actions_from_response(response(("c1", "exec", {"target": "pwd"}),
                                           ("c1", "exec", {"target": "ls"})), "candidate")

    def test_runner_executes_batch_in_order_and_returns_both_tool_results(self):
        class Environment:
            def __init__(self, case):
                self.history = []
                self.done = False
                self.reason = None
            def contract(self):
                return {"task": "fixture"}
            def observation(self):
                return {"steps_remaining": 10 - len(self.history), "done": self.done}
            def evidence(self):
                return {"calls": []}
            def grade(self):
                return {"success": self.done and self.reason == "finished",
                        "termination": self.reason, "steps": len(self.history)}
            def start(self):
                pass
            def step(self, action):
                if action["command"] == "finish":
                    self.done, self.reason = True, "finished"
                result = self.observation()
                self.history.append({"action": action, "observation": result})
                return result
            def abort(self, reason):
                self.done, self.reason = True, reason
            def close(self):
                pass

        suite = {"cases": [{"max_steps": 10}]}
        plan = {"study_id": "fixture", "framework_version": __version__,
                "models": ["candidate"], "suite_sha256": digest(suite),
                "source_sha256": {}, "runtime": {},
                "transport": {"stream": True, "base_url": "https://example.test/v1",
                              "max_wire_attempts_per_turn": 2},
                "interface": {"kind": "boyue-chat-tools/2",
                              "request_options_by_model": {"candidate": {"parallel_tool_calls": False}}},
                "limits": {"wall_seconds": 60, "request_seconds": 10, "response_bytes": 10000}}
        seen_messages = []
        replies = [response(("c1", "exec", {"target": "pwd"}),
                            ("c2", "exec", {"target": "ls"})),
                   response(("c3", "finish", {}))]
        def send(_url, _key, payload, _audit, **_kwargs):
            seen_messages.append(copy.deepcopy(payload["messages"]))
            return replies[len(seen_messages) - 1]
        with tempfile.TemporaryDirectory() as temporary:
            plan_path = Path(temporary) / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with (patch("tools.boyue_chat_stream_v3.suite", return_value=suite),
                  patch("tools.boyue_chat_stream_v3.StreamEnvironment", Environment),
                  patch("tools.boyue_chat_stream_v3.configuration", return_value={}),
                  patch("tools.boyue_chat_stream_v3.core.registration",
                        return_value=("https://example.test/v1", "key")),
                  patch("tools.boyue_chat_stream_v3.wire.exchange", side_effect=send)):
                record = run(plan_path, "candidate", Path(temporary) / "output")
        self.assertTrue(record["grade"]["success"])
        self.assertEqual([event["action"]["command"] for event in record["events"]],
                         ["exec", "exec", "finish"])
        self.assertEqual([item["tool_call_id"] for item in seen_messages[1] if item["role"] == "tool"],
                         ["c1", "c2"])
        self.assertEqual(record["usage"]["requests"], 2)


if __name__ == "__main__":
    unittest.main()
