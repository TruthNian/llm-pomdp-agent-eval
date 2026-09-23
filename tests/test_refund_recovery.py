import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from pomdp_bench.collection import validate_definition
from pomdp_bench.evaluation import run_episode, replay, replay_environment
from pomdp_bench.refund_control import policy_action, DECODE, PROJECT, DISPATCH
from pomdp_bench.refund_recovery import make_case, suite
from pomdp_bench.refund_runtime import Runtime
from pomdp_bench.refund_rules import run
from pomdp_bench.worlds import Environment

OPERATOR = {"name": "reference", "kind": "refund_operator"}


def episode(variant="complete"):
    with patch("pomdp_bench.agents.refund_action", side_effect=lambda r: policy_action(r, variant)):
        return run_episode(make_case(), OPERATOR, "open", 0)


class RefundTests(unittest.TestCase):
    def test_public_reference_replay_and_fresh_execution(self):
        record = json.loads(json.dumps(episode()))
        self.assertTrue(record["grade"]["success"])
        self.assertEqual(record["grade"]["invalid_actions"], 0)
        replay(record, make_case())
        replay_environment(record, make_case(), execute_checks=True)
        changed = copy.deepcopy(record)
        changed["service_evidence"]["calls"][0]["action"]["target"] = "source"
        with self.assertRaises(ValueError):
            replay(changed, make_case())

    def test_partial_repairs_and_allocation_counterexample(self):
        for variant in ("new_keys", "updated_only", "charge_amount", "order_identity", "same_failed_key", "no_refresh", "swapped_allocations"):
            with self.subTest(variant=variant):
                grade = episode(variant)["grade"]
                self.assertFalse(grade["success"], grade)
                self.assertEqual(grade["invalid_actions"], 0)
                if variant == "new_keys":
                    self.assertEqual(grade["excess_refunded_cents"], 150)
                    self.assertGreater(grade["external_errors"], 0)
                elif variant == "swapped_allocations":
                    self.assertEqual(grade["external_errors"], 0)
                    self.assertEqual(grade["book_errors"], 0)
                    self.assertEqual(grade["intent_errors"], 4)
                elif variant in ("updated_only", "charge_amount", "order_identity"):
                    self.assertEqual(grade["external_errors"], 0)
                    self.assertGreater(grade["projection_errors"], 0)

    def test_sql_cannot_access_provider_or_host(self):
        for sql in ("SELECT * FROM operations", "SELECT * FROM sqlite_master", "ATTACH DATABASE 'provider.sqlite' AS p", "SELECT load_extension('x')", "SELECT randomblob(1000000000)"):
            with self.subTest(sql=sql), self.assertRaises((ValueError, sqlite3.Error)):
                run(sql, "dispatch", [])

    def test_key_ownership_and_atomic_dispatch_validation(self):
        runtime = Runtime(make_case())
        try:
            before = runtime.prows("SELECT * FROM operations")
            bad = DISPATCH.replace("request_key AS key", "'one-key' AS key")
            runtime.connection.execute("UPDATE rules SET active=? WHERE stage='dispatch'", (bad,))
            runtime.call({"command": "configure", "target": {"enabled": True}})
            self.assertEqual(runtime.prows("SELECT * FROM operations"), before)
            self.assertTrue(runtime.audit()["worker_error"])
            runtime.settings["enabled"] = False
            result = runtime.call({"command": "retry", "target": {"intent_id": "order-a/intent-2", "key": "order-a/refund-1"}})
            self.assertIn("error", result["result"])
            self.assertEqual(runtime.rows("SELECT request_key FROM refund_intents WHERE intent_id='order-a/intent-2'")[0]["request_key"], "order-a/refund-2")
        finally:
            runtime.close()

    def test_deploy_does_not_backfill_and_projection_cannot_hide_bad_rows(self):
        record = episode()
        runtime = Runtime(make_case())
        try:
            for call in record["service_evidence"]["calls"]:
                self.assertEqual(runtime.call(call["action"]), call["response"])
            self.assertTrue(runtime.call({"command": "verify"})["result"]["passed"])
            # Preserve the total while changing individual refund amounts.
            runtime.connection.execute("UPDATE projection SET amount_cents=amount_cents+CASE WHEN operation_id=(SELECT min(operation_id) FROM projection WHERE order_id='order-a' AND kind='refund') THEN 1 ELSE -1 END WHERE order_id='order-a' AND kind='refund'")
            self.assertFalse(runtime.audit()["book_mismatches"])
            self.assertEqual(runtime.audit()["projection_errors"], 2)
            self.assertFalse(runtime.call({"command": "verify"})["result"]["passed"])
        finally:
            runtime.close()
        runtime = Runtime(make_case())
        try:
            before = runtime.rows("SELECT * FROM projection")
            for stage, sql in (("decode", DECODE), ("project", PROJECT), ("dispatch", DISPATCH)):
                runtime.call({"command": "patch", "target": {"stage": stage, "sql": sql}})
            operations = runtime.prows("SELECT * FROM operations")
            runtime.call({"command": "test"})
            # Due settlements may change statuses at the normal tick; SQL sends no new requests.
            self.assertEqual(len(operations), len(runtime.prows("SELECT * FROM operations")))
            runtime.call({"command": "deploy"})
            self.assertEqual(before, runtime.rows("SELECT * FROM projection"))
            self.assertFalse(runtime.audit()["projection_current"])
        finally:
            runtime.close()

    def test_local_adjustment_cannot_undo_external_money(self):
        record = episode("new_keys")
        runtime = Runtime(make_case())
        try:
            for call in record["service_evidence"]["calls"]:
                runtime.call(call["action"])
            transfers = runtime.prows("SELECT * FROM transfers")
            runtime.call({"command": "adjust", "target": {"order_id": "order-a", "delta_cents": 150, "key": "books"}})
            self.assertEqual(runtime.prows("SELECT * FROM transfers"), transfers)
            self.assertEqual(runtime.audit()["excess_refunded_cents"], 150)
        finally:
            runtime.close()

    def test_stable_verify_stale_pass_and_version_gate(self):
        record = episode()
        actions = [e["action"] for e in record["events"]]
        changed = {"name": "stale", "kind": "actions", "actions": actions[:-1]+[{"command": "wait"}, {"command": "finish"}]}
        self.assertFalse(run_episode(make_case(), changed, "open", 0)["grade"]["success"])
        with self.assertRaises(ValueError):
            Environment(make_case(), framework_version="2.11.0")
        validate_definition(suite(), [OPERATOR], ["open"], 1, 3600)
        with self.assertRaises(ValueError):
            validate_definition(suite(), [{"name": "wrong", "kind": "settlement_operator"}], ["open"], 1, 3600)


if __name__ == "__main__":
    unittest.main()
