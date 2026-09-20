"""Exercise actual HTTP/SQLite effects, outcome separation, replay and cleanup."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pomdp_bench.collection import run_suite, read_run
from pomdp_bench.evaluation import run_episode, replay, replay_environment
from pomdp_bench.incident import IncidentEnvironment, make_case, suite
from pomdp_bench.incident_runtime import Runtime


OPERATOR = {"name": "runbook-operator", "kind": "incident_operator"}
CONFIGURE = {"command": "configure", "target": {"service": "worker", "patch": {"protocol": "compatible", "dedupe": "order", "batch": 16}}}
RESTART = {"command": "restart", "target": "worker"}
VERIFY, FINISH = {"command": "verify"}, {"command": "finish"}


class IncidentTests(unittest.TestCase):
    def test_public_operator_delivers_real_work_and_both_replays_agree(self):
        trace = run_episode(make_case(), OPERATOR, "open", 0)
        self.assertTrue(trace["grade"]["success"])
        self.assertGreater(trace["grade"]["http_requests"], 30)
        self.assertGreater(trace["grade"]["excess_debit_cent_ticks"], 0)
        self.assertEqual(trace["grade"]["accounting_mismatches"], 0)
        with patch("pomdp_bench.incident.Runtime", side_effect=AssertionError("Replay must not start services")):
            self.assertEqual(replay(trace, make_case()), trace["grade"])
        fresh = replay_environment(trace, make_case(), execute_checks=True)
        self.assertEqual(fresh.grade(), trace["grade"])
        self.assertTrue(fresh.runtime.closed)
        self.assertFalse(fresh.runtime.db.exists())

    def test_green_process_and_config_fix_do_not_erase_business_damage(self):
        for actions in ([{"command": "inspect", "target": "metrics"}, FINISH],
                        [CONFIGURE, VERIFY, FINISH],
                        [CONFIGURE, RESTART, VERIFY, FINISH],
                        [{"command": "rollback", "target": "worker"}, VERIFY, FINISH]):
            with self.subTest(actions=actions):
                trace = run_episode(make_case(), {"name": "incomplete", "kind": "actions", "actions": actions}, "open", 0)
                self.assertFalse(trace["grade"]["success"])
                self.assertGreater(trace["grade"]["accounting_mismatches"], 0)

    def test_later_observation_advances_work_and_expires_verification(self):
        reference = run_episode(make_case(), OPERATOR, "open", 0)
        actions = [e["action"] for e in reference["events"][:-1]]
        trace = run_episode(make_case(), {"name": "stale", "kind": "actions", "actions": [*actions, {"command": "inspect", "target": "metrics"}, FINISH]}, "open", 0)
        self.assertFalse(trace["grade"]["success"])
        self.assertFalse(trace["grade"]["verified_current_state"])

    def test_rejected_final_actions_cannot_skip_scheduled_traffic(self):
        for action in ({"command": "finish", "target": "invalid"},
                       {"command": "verify", "target": "invalid"},
                       {"command": "verify", "extra": "invalid"}):
            with self.subTest(action=action):
                env = IncidentEnvironment(make_case())
                try:
                    for _ in range(18):
                        self.assertIn("error", env.step(action)["result"])
                    self.assertEqual(env.last_response["audit"]["order_count"], 25)
                    self.assertEqual(env.grade()["steps"], 18)
                    self.assertEqual(env.grade()["invalid_actions"], 18)
                    self.assertFalse(env.done)
                finally:
                    env.close()

    def test_sql_is_useful_but_read_only_and_resources_close(self):
        env = IncidentEnvironment(make_case())
        try:
            result = env.step({"command": "query", "target": "SELECT o.order_id,o.amount_cents,sum(l.amount_cents) AS paid FROM orders o JOIN ledger l USING(order_id) GROUP BY o.order_id"})["result"]
            self.assertEqual(result["rows"], [["pending-7", 1299, 2598]])
            for sql in ("DELETE FROM orders", "ATTACH DATABASE ':memory:' AS injected", "PRAGMA writable_schema=ON"):
                self.assertIn("error", env.step({"command": "query", "target": sql})["result"])
            result = env.step({"command": "query", "target": "SELECT count(*) FROM orders"})["result"]
            self.assertGreaterEqual(result["rows"][0][0], 7)
            path = env.runtime.db
        finally:
            env.close()
        self.assertFalse(path.exists())

    def test_checkpoint_storage_failure_closes_services(self):
        created = []
        def runtime(case):
            result = Runtime(case)
            created.append(result)
            return result
        def checkpoint(record):
            if record["events"]:
                raise OSError("storage unavailable")
        with patch("pomdp_bench.incident.Runtime", side_effect=runtime):
            with self.assertRaises(OSError):
                run_episode(make_case(), OPERATOR, "open", 0, checkpoint=checkpoint)
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].closed)
        self.assertFalse(created[0].db.exists())

    def test_collector_retains_failures_and_binds_every_live_action(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "run"
            report = run_suite(suite(), [OPERATOR, {"name": "early", "kind": "actions", "actions": [FINISH]}], ["open"], 1, directory)
            self.assertEqual(report["episodes"], 2)
            self.assertEqual([r["successes"] for r in report["overall"]], [0, 1])
            _, traces = read_run(directory)
            trace = copy.deepcopy(next(r for r in traces if r["grade"]["success"]))
            trace["service_evidence"]["calls"][0]["request_sha256"] = "wrong"
            with self.assertRaises(ValueError):
                replay(trace, make_case())


if __name__ == "__main__":
    unittest.main()
