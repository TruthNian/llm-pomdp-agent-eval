"""Fault injection at request and commit boundaries, not just happy-path resume."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pomdp_bench.agents import ScriptedAgent
from pomdp_bench.cli import main
from pomdp_bench.collection import prepare_suite, resume_suite, run_status, run_suite
from pomdp_bench.environment import Environment
from pomdp_bench.evaluation import episode_record, replay, run_episode
from pomdp_bench.generator import digest, generate, suite
from pomdp_bench.reporting import summarize, validate_run
from pomdp_bench.storage import collection_lock, read_json, write_json

CONFIGS = [{"name": "reference", "kind": "reference"}]


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "run"
        self.data = suite([7, 8], families=["diagnosis"])

    def prepare(self):
        return prepare_suite(self.data, CONFIGS, ["open"], 1, self.out)

    def test_prepare_status_and_resume_are_idempotent_and_never_redial_completed(self):
        with patch("pomdp_bench.evaluation.make_agent", side_effect=AssertionError("No calls while preparing")):
            self.prepare()
            self.assertEqual(run_status(self.out)["pending"], 2)
        report = resume_suite(self.out)
        self.assertEqual(report["overall"][0]["successes"], 2)
        before = {p: p.read_bytes() for p in (self.out / "private").rglob("*.json")}
        with patch("pomdp_bench.evaluation.make_agent", side_effect=AssertionError("Must never rerun")):
            self.assertEqual(resume_suite(self.out), report)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_interrupt_mid_request_preserves_partial_history_and_denominator(self):
        self.prepare()
        reference = ScriptedAgent("reference", 0)
        calls = 0

        def act(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return reference.act(request, timeout)

        with patch("pomdp_bench.evaluation.make_agent") as maker:
            maker.return_value.act.side_effect = act
            maker.return_value.usage = {"requests": 1, "requests_with_usage": 1,
                                       "input_tokens": 12, "output_tokens": 3}
            with self.assertRaises(KeyboardInterrupt):
                resume_suite(self.out)
        self.assertEqual(run_status(self.out)["interrupted_unsealed"], 1)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            validate_run(self.out)
        report = resume_suite(self.out)
        _, records = validate_run(self.out)
        failed = next(r for r in records if not r["grade"]["success"])
        self.assertEqual(failed["grade"]["termination"], "collection_interrupted")
        self.assertEqual(len(failed["events"]), 1)
        self.assertGreater(failed["grade"]["cost"], 0)
        self.assertTrue(failed["request_in_flight"])
        self.assertIsNone(failed["usage"])
        self.assertEqual(failed["partial_usage"]["input_tokens"], 12)
        row = report["overall"][0]
        self.assertEqual((row["successes"], row["episodes"], row["collection_failures"]), (1, 2, 1))
        self.assertEqual(row["elapsed_lower_bound_episodes"], 1)
        self.assertIsNone(row["total_input_tokens"])

    def test_terminal_checkpoint_survives_crash_before_trace_commit(self):
        self.prepare()
        original = write_json

        def crash(path, value, **kwargs):
            if path.parent.name == "traces":
                raise KeyboardInterrupt()
            return original(path, value, **kwargs)

        with patch("pomdp_bench.collection.write_json", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                resume_suite(self.out)
        report = resume_suite(self.out)
        self.assertEqual(report["overall"][0]["successes"], 2)
        _, records = validate_run(self.out)
        self.assertEqual(sum(r.get("recovered_from_checkpoint", False) for r in records), 1)

    def test_trace_survives_crash_before_receipt_without_overwrite(self):
        self.prepare()
        original = write_json

        def crash(path, value, **kwargs):
            if path.parent.name == "receipts":
                raise KeyboardInterrupt()
            return original(path, value, **kwargs)

        with patch("pomdp_bench.collection.write_json", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                resume_suite(self.out)
        trace = next((self.out / "private" / "traces").glob("*.json"))
        before = trace.read_bytes()
        resume_suite(self.out)
        self.assertEqual(trace.read_bytes(), before)
        validate_run(self.out)

    def test_storage_failure_is_not_an_adapter_error(self):
        self.prepare()
        original = write_json

        def fail(path, value, **kwargs):
            if path.parent.name == "checkpoints":
                raise OSError("Disk full")
            return original(path, value, **kwargs)

        with patch("pomdp_bench.collection.write_json", side_effect=fail):
            with self.assertRaisesRegex(OSError, "Disk full"):
                resume_suite(self.out)
        report = resume_suite(self.out)
        self.assertEqual(report["overall"][0]["collection_failures"], 1)
        self.assertEqual(report["overall"][0]["adapter_failures"], 0)

    def test_committed_failures_are_not_retried(self):
        configs = [{"name": "failed", "kind": "chat", "model": "fixture", "endpoint_env": "E", "api_key_env": "K"}]
        with patch.dict(os.environ, {}, clear=True):
            run_suite(self.data, configs, ["open"], 1, self.out)
        with patch("pomdp_bench.evaluation.make_agent", side_effect=AssertionError("No retries")):
            report = resume_suite(self.out)
        self.assertEqual(report["overall"][0]["adapter_failures"], 2)

    def test_receipt_detects_changed_or_deleted_trace_before_any_calls(self):
        run_suite(self.data, CONFIGS, ["open"], 1, self.out)
        trace = next((self.out / "private" / "traces").glob("*.json"))
        record = read_json(trace)
        record["elapsed_seconds"] += 1
        write_json(trace, record)
        with self.assertRaisesRegex(ValueError, "receipt"):
            resume_suite(self.out)
        trace.unlink()
        with self.assertRaisesRegex(ValueError, "committed evidence"):
            resume_suite(self.out)

    def test_source_and_configuration_drift_cannot_mix_into_a_run(self):
        self.prepare()
        with patch("pomdp_bench.collection.source_hashes", return_value={}):
            with self.assertRaisesRegex(ValueError, "original collection"):
                resume_suite(self.out)
        manifest_path = self.out / "private" / "manifest.json"
        # An altered plan is detected once an attempt is bound to its fingerprint.
        with patch("pomdp_bench.collection.run_episode", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                resume_suite(self.out)
        manifest = read_json(manifest_path)
        manifest["wall_seconds_per_episode"] += 1
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            resume_suite(self.out)

    def test_individually_valid_checkpoint_cannot_rewrite_committed_action_history(self):
        run_suite(self.data, CONFIGS, ["open"], 1, self.out)
        path = next((self.out / "private" / "checkpoints").glob("*.json"))
        original = read_json(path)
        # Pick the checkpoint's actual case, then construct a different valid history.
        case = next(c for c in self.data["cases"] if digest(c) == original["case_id"])
        env = Environment(case)
        env.step({"command": "status"})
        for event in original["events"]:
            env.step(event["action"])
        alternate = episode_record(env, CONFIGS[0], 0)
        alternate["suite_sha256"] = original["suite_sha256"]
        replay(alternate, case)  # Valid in isolation; inconsistent with its committed run.
        write_json(path, alternate)
        with self.assertRaisesRegex(ValueError, "not a prefix"):
            validate_run(self.out)

    def test_duplicate_conditions_in_manifest_are_rejected(self):
        self.prepare()
        path = self.out / "private" / "manifest.json"
        manifest = read_json(path)
        manifest["conditions"] = ["open", "open"]
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "duplicate conditions"):
            resume_suite(self.out)

    def test_prepared_budget_cannot_change_before_first_call(self):
        self.prepare()
        path = self.out / "private" / "manifest.json"
        manifest = read_json(path)
        manifest["wall_seconds_per_episode"] += 1
        write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "Prepared manifest mismatch"):
            resume_suite(self.out)

    def test_old_trace_replays_but_mixed_versions_cannot_be_pooled(self):
        a = run_episode(generate(7), CONFIGS[0], "open", 0)
        b = copy.deepcopy(a)
        b["framework_version"] = "2.0.0"
        b["agent"]["name"] = "legacy"
        del b["request_in_flight"]
        replay(b, generate(7))
        with self.assertRaisesRegex(ValueError, "framework versions"):
            summarize([a, b])
        b["clairvoyant_action_cost_lower_bound"] += 1
        with self.assertRaisesRegex(ValueError, "cost bound"):
            replay(b, generate(7))

    def test_real_process_crash_releases_lock_and_does_not_retry_inflight_episode(self):
        self.prepare()
        program = '''
import os, sys
from pathlib import Path
from unittest.mock import patch
from pomdp_bench.collection import resume_suite
with patch("pomdp_bench.agents.ScriptedAgent.act", side_effect=lambda *a, **k: os._exit(73)):
    resume_suite(Path(sys.argv[1]))
'''
        process = subprocess.run([sys.executable, "-c", program, str(self.out)], capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 73, process.stderr.decode(errors="replace"))
        report = resume_suite(self.out)
        self.assertEqual(report["overall"][0]["collection_failures"], 1)
        self.assertEqual(report["overall"][0]["successes"], 1)

    def test_competing_process_is_rejected_while_collector_holds_lock(self):
        self.prepare()
        program = '''
import sys
from pathlib import Path
from pomdp_bench.collection import resume_suite
try:
    resume_suite(Path(sys.argv[1]))
except ValueError as exc:
    print(str(exc))
    sys.exit(27)
'''
        with collection_lock(self.out):
            process = subprocess.run([sys.executable, "-c", program, str(self.out)], capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 27, process.stderr.decode(errors="replace"))
        self.assertIn(b"locked by another collector", process.stdout)
        self.assertEqual(run_status(self.out)["pending"], 2)

    def test_cli_prepare_status_resume(self):
        path = Path(self.temp.name) / "suite.json"
        write_json(path, self.data)
        self.assertEqual(main(["prepare", "--suite", str(path), "--out", str(self.out)]), 0)
        self.assertEqual(main(["status", str(self.out)]), 0)
        self.assertEqual(main(["resume", str(self.out)]), 0)
        self.assertEqual(main(["validate", str(self.out)]), 0)


if __name__ == "__main__":
    unittest.main()
