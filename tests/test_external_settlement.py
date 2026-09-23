"""Business consequences, information boundary, counterfactuals and replay."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from pomdp_bench.collection import read_run, run_suite, validate_definition
from pomdp_bench.evaluation import run_episode, replay, replay_environment
from pomdp_bench.settlement import make_case, suite, policy_action
from pomdp_bench.settlement_runtime import Runtime
from pomdp_bench.worlds import validate_case_version

OPERATOR = {"name": "public-operator", "kind": "settlement_operator"}


class SettlementTests(unittest.TestCase):
    def test_public_operator_delivers_and_both_replays_agree(self):
        row = run_episode(make_case(), OPERATOR, "open", 0)
        self.assertTrue(row["grade"]["success"], row)
        self.assertEqual(row["grade"]["additional_excess_settled_cents"], 0)
        self.assertGreater(row["grade"]["http_requests"], 10)
        with patch("pomdp_bench.settlement.Runtime", side_effect=AssertionError("recorded replay must be offline")):
            self.assertEqual(replay(row, make_case()), row["grade"])
        self.assertEqual(replay_environment(row, make_case(), execute_checks=True).grade(), row["grade"])
        changed = copy.deepcopy(row)
        changed["service_evidence"]["calls"][0]["request_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            replay(changed, make_case())

    def test_notification_delay_and_deadline_counterfactuals(self):
        arrival = lambda r: policy_action(r, event_order="arrival")
        def delayed(r):
            return {"command": "wait"} if len(r["history"]) < 12 else policy_action(r)
        for policy, rescued in ((arrival, "immediate_events"), (delayed, "no_cancel_deadline")):
            with patch("pomdp_bench.agents.settlement_action", side_effect=policy):
                full = run_episode(make_case(), OPERATOR, "open", 0)
                ablated = run_episode(make_case(rescued), OPERATOR, "open", 0)
            self.assertFalse(full["grade"]["success"], full)
            self.assertTrue(ablated["grade"]["success"], ablated)
            if rescued == "immediate_events":
                self.assertEqual(full["grade"]["external_mismatches"], 0)
                self.assertGreater(full["grade"]["book_mismatches"], 0)
            else:
                self.assertEqual(full["grade"]["additional_excess_settled_cents"], 1200)

    def test_post_commit_errors_and_identity_change_actual_transfers(self):
        with patch("pomdp_bench.agents.settlement_action", side_effect=lambda r: policy_action(r, retry_identity="attempt")):
            row = run_episode(make_case(), OPERATOR, "open", 0)
        self.assertFalse(row["grade"]["success"])
        self.assertGreater(row["grade"]["additional_excess_settled_cents"], 0)
        self.assertGreater(row["grade"]["external_mismatches"], 0)

    def test_provider_is_separate_and_local_adjustment_cannot_refund(self):
        runtime = Runtime(make_case())
        try:
            tables = runtime.query("SELECT name FROM sqlite_master")
            self.assertNotIn(["operations"], tables["rows"])
            for sql in ("SELECT * FROM operations", "ATTACH DATABASE 'provider.sqlite' AS p", "DELETE FROM orders"):
                self.assertIn("error", runtime.call({"command": "query", "target": sql})["result"])
            before = runtime.prows("SELECT * FROM transfers")
            result = runtime.call({"command": "adjust", "target": {"order_id": "order-b", "delta_cents": -800, "key": "book-only"}})
            self.assertFalse(result["result"]["external_effect"])
            self.assertEqual(runtime.prows("SELECT * FROM transfers"), before)
            self.assertIn("order-b", [m["order_id"] for m in runtime.audit()["external_mismatches"]])
        finally:
            runtime.close()
        self.assertFalse(runtime.db.exists())

    def test_finite_funding_failed_refund_and_same_key_do_not_reset_state(self):
        runtime = Runtime(make_case())
        try:
            for _ in range(4):
                runtime.call({"command": "wait"})
            failed = runtime.object("op-5")
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(runtime.http("/fund", {"amount_cents": 800})[0], 200)
            self.assertEqual(runtime.http("/fund", {"amount_cents": 1})[0], 409)
            request = {"order_id": "order-b", "amount_cents": 800, "key": failed["key"], "parent_id": failed["parent_id"]}
            self.assertEqual(runtime.http("/refund", request)[1]["status"], "failed")
            request["key"] = "recovery"
            created = runtime.http("/refund", request)[1]
            self.assertEqual(created["status"], "pending")
            # Verification is not a hidden settlement engine, regardless of repeats.
            state = runtime.tables()
            for _ in range(10):
                self.assertFalse(runtime.call({"command": "verify"})["result"]["passed"])
            self.assertEqual(runtime.tables(), state)
            for _ in range(4):
                runtime.call({"command": "wait"})
            self.assertEqual(runtime.object(created["operation_id"])["status"], "succeeded")
            self.assertEqual(runtime.prows("SELECT available_cents FROM wallet")[0]["available_cents"], 0)
        finally:
            runtime.close()

    def test_cancellation_boundary_is_irreversible_and_invalid_final_advances(self):
        for tick, expected in ((11, 200), (12, 409)):
            runtime = Runtime(make_case())
            try:
                for _ in range(tick):
                    result = runtime.call({"command": "verify", "target": "invalid"})
                    self.assertIn("error", result["result"])
                self.assertEqual(runtime.tick, tick)
                self.assertEqual(runtime.http("/cancel", {"operation_id": "op-2"})[0], expected)
                if tick == 12:
                    self.assertEqual(runtime.audit()["additional_excess_settled_cents"], 1200)
            finally:
                runtime.close()

    def test_success_expires_after_another_action_and_early_finish_fails(self):
        row = run_episode(make_case(), OPERATOR, "open", 0)
        actions = [e["action"] for e in row["events"]]
        for changed in (actions[:-1] + [{"command": "wait"}, {"command": "finish"}], [{"command": "finish"}]):
            result = run_episode(make_case(), {"name": "changed", "kind": "actions", "actions": changed}, "open", 0)
            self.assertFalse(result["grade"]["success"])

    def test_collection_version_binding_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_suite(suite(), [OPERATOR], ["open"], 1, Path(tmp) / "run")
            _, rows = read_run(Path(tmp) / "run")
            self.assertEqual(rows[0]["cluster_unit"], "incident_scenario")
            self.assertTrue(rows[0]["grade"]["success"])
        with self.assertRaises(ValueError):
            validate_case_version(make_case(), "2.9.2")
        with self.assertRaises(ValueError):
            validate_definition(suite(), [{"name": "wrong", "kind": "incident_operator"}], ["open"], 1, 60)


if __name__ == "__main__":
    unittest.main()
