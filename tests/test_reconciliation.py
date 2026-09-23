import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pomdp_bench.collection import prepare_suite, validate_definition
from pomdp_bench.evaluation import episode_record, replay, replay_environment
from pomdp_bench.generator import digest
from pomdp_bench.reconciliation import ReconciliationEnvironment, make_case, suite
from pomdp_bench.reconciliation_control import AGGREGATE, correction, policy_action
from pomdp_bench.reconciliation_data import CONTRACTS, PROFILES, SHAPES, batch
from pomdp_bench.reconciliation_runtime import Runtime
from pomdp_bench.reconciliation_sql import minor, pipeline, transform
from pomdp_bench.worlds import Environment, cluster_id


def episode(profile, variant="complete"):
    env = ReconciliationEnvironment(make_case(profile))
    try:
        while not env.done:
            env.step(policy_action({"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}, variant))
        return episode_record(env, {"name": variant, "kind": "actions", "actions": [e["action"] for e in env.history]}, 0)
    finally:
        env.close()


class ReconciliationTests(unittest.TestCase):
    def test_public_control_full_replay_and_fresh_execution(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                record = json.loads(json.dumps(episode(profile)))
                self.assertTrue(record["grade"]["success"])
                self.assertEqual(record["grade"]["workload_batches"], 2)
                self.assertEqual(record["grade"]["invalid_actions"], 0)
                replay(record, make_case(profile))
                replay_environment(record, make_case(profile), execute_checks=True)
                changed = copy.deepcopy(record)
                changed["service_evidence"]["calls"][0]["action"]["target"] = "source"
                with self.assertRaises(ValueError):
                    replay(changed, make_case(profile))

    def test_partial_repairs_do_not_solve_portfolio(self):
        for profile in PROFILES:
            for variant in ("normalize_only", "fixed_resolver", "global_identity", "no_refresh"):
                with self.subTest(profile=profile, variant=variant):
                    record = episode(profile, variant)
                    self.assertFalse(record["grade"]["success"])
                    self.assertEqual(record["grade"]["invalid_actions"], 0)
        self.assertFalse(episode("capture_snapshots", "no_epoch")["grade"]["success"])
        self.assertTrue(episode("posting_corrections", "no_epoch")["grade"]["success"])
        self.assertFalse(episode("posting_corrections", "positive_only")["grade"]["success"])

    def test_sql_input_isolation_and_bounded_execution(self):
        invalid = ["ATTACH DATABASE 'provider.sqlite' AS provider", "DELETE FROM receipts",
                   "SELECT * FROM sqlite_master", "SELECT load_extension('missing')",
                   "SELECT randomblob(1000000000)", "SELECT * FROM truth",
                   "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT sum(n) FROM x"]
        for sql in invalid:
            with self.subTest(sql=sql), self.assertRaises((ValueError, sqlite3.Error)):
                transform(sql, "normalize", [])
        with self.assertRaises(ValueError):
            transform("SELECT 1.5 AS receipt,'m' AS merchant,'o' AS object,'USD' AS currency,0 AS epoch,1 AS revision,2 AS amount_minor", "normalize", [])
        with self.assertRaises(ValueError):
            transform("WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x WHERE n<300) SELECT n AS receipt,'m' AS merchant,'o' AS object,'USD' AS currency,0 AS epoch,1 AS revision,2 AS amount_minor FROM x", "normalize", [])

    def test_exact_money_and_contract_generalization(self):
        self.assertEqual(minor("1.234", "KWD", "major"), 1234)
        self.assertEqual(minor("901", "JPY", "major"), 901)
        self.assertEqual(minor("12.01", "USD", "major"), 1201)
        for amount in ("1.001", "NaN", "Infinity", "1e9999"):
            with self.assertRaises(ValueError):
                minor(amount, "USD", "major")
        # Nonfixture names and amounts: this is a metamorphic component check,
        # NOT a held-out model episode or another independent benchmark task.
        body = {"account": "new-merchant", "entry_id": "arbitrary-entry", "invoice_id": "shared",
                "currency": "KWD", "revision": 7, "kind": "refund", "status": "posted", "amount": "3.789", "unit": "major"}
        output = pipeline(correction(CONTRACTS["posting_corrections"]), [[1, json.dumps(body)], [2, json.dumps(body)]])
        self.assertEqual(output["resolve"], [["new-merchant", "arbitrary-entry", "KWD", -3789]])
        self.assertEqual(output["aggregate"], [["new-merchant", "KWD", -3789]])

    def test_deploy_and_refresh_are_separate_and_atomic(self):
        runtime = Runtime(make_case("posting_corrections"))
        directory = Path(runtime.temp.name)
        try:
            before = runtime.rows("SELECT * FROM report")
            for stage, sql in correction(CONTRACTS["posting_corrections"]).items():
                runtime.call({"command": "patch", "target": {"stage": stage, "sql": sql}})
            runtime.call({"command": "deploy"})
            self.assertEqual(before, runtime.rows("SELECT * FROM report"))
            self.assertFalse(runtime.audit()["output_current"])
            self.assertNotIn("error", runtime.call({"command": "refresh"})["result"])
            self.assertEqual(runtime.audit()["position_errors"], 0)
            active = runtime.sources("active")
            runtime.call({"command": "patch", "target": {"stage": "aggregate", "sql": "SELECT * FROM truth"}})
            self.assertIn("error", runtime.call({"command": "deploy"})["result"])
            self.assertEqual(active, runtime.sources("active"))
            self.assertIn("error", runtime.call({"command": "query", "target": "SELECT * FROM truth"})["result"])
            # Current provider evidence cannot mutate or backfill local output.
            report = runtime.rows("SELECT * FROM report")
            runtime.call({"command": "provider", "target": "all"})
            self.assertEqual(report, runtime.rows("SELECT * FROM report"))
        finally:
            runtime.close()
        self.assertFalse(directory.exists())

    def test_oracle_does_not_reuse_sql_and_lineage_matters(self):
        runtime = Runtime(make_case("capture_snapshots"))
        try:
            # A perfectly forged total with wrong individual positions must fail.
            totals = runtime.prows("SELECT merchant,currency,sum(amount_minor) AS net_minor FROM truth GROUP BY merchant,currency")
            runtime.connection.execute("DELETE FROM report")
            runtime.connection.executemany("INSERT INTO report VALUES (?,?,?)", [tuple(r.values()) for r in totals])
            self.assertEqual(runtime.audit()["report_errors"], 0)
            self.assertGreater(runtime.audit()["position_errors"], 0)
            runtime.provider.execute("UPDATE truth SET amount_minor=amount_minor+1 WHERE merchant='east'")
            self.assertGreater(runtime.audit()["report_errors"], 0)
        finally:
            runtime.close()

    def test_stable_verification_rejections_and_stale_pass(self):
        record = episode("capture_snapshots")
        env = ReconciliationEnvironment(make_case())
        try:
            for event in record["events"][:-1]:
                env.step(event["action"])
            self.assertTrue(env.observation()["verification_current"])
            state = digest(env.runtime.tables())
            env.step({"command": "verify"})
            self.assertEqual(digest(env.runtime.tables()), state)
            env.step({"command": "verify", "target": "invalid"})
            self.assertFalse(env.observation()["verification_current"])
            self.assertNotEqual(digest(env.runtime.tables()), state)
            env.step({"command": "finish"})
            self.assertFalse(env.grade()["success"])
        finally:
            env.close()

    def test_version_collection_and_clusters(self):
        with self.assertRaises(ValueError):
            Environment(make_case(), framework_version="2.10.0")
        config = [{"name": "control", "kind": "reconciliation_operator"}]
        validate_definition(suite(), config, ["open"], 1, 300)
        with self.assertRaises(ValueError):
            validate_definition(suite(), [{"name": "wrong", "kind": "settlement_operator"}], ["open"], 1, 300)
        self.assertNotEqual(cluster_id(make_case(PROFILES[0])), cluster_id(make_case(PROFILES[1])))
        with tempfile.TemporaryDirectory() as temporary:
            manifest = prepare_suite(suite(), config, ["open"], 1, Path(temporary)/"run")
            self.assertEqual(manifest["expected_episodes"], 2)


if __name__ == "__main__":
    unittest.main()
