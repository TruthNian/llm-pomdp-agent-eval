"""State/provenance tests only; real candidate execution belongs to container CI."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from pomdp_bench.evaluation import replay, run_episode, validate_suite
from pomdp_bench.generator import digest
from pomdp_bench.repair import RepairEnvironment, make_case, suite
from pomdp_bench.repair_checks import assess_rows
from pomdp_bench.repair_portfolio import ROOT, TASKS, VERSION
from pomdp_bench.repair_portfolio_checks import selected
from pomdp_bench.worlds import cluster_id, validate_case, validate_case_version
from unittest.mock import patch

IMAGE = "sha256:" + "0" * 64


class PortfolioTests(unittest.TestCase):
    def test_three_source_tasks_are_pinned_and_versioned(self):
        data = suite(IMAGE, list(TASKS))
        validate_suite(data)
        self.assertEqual(data["generator_version"], VERSION)
        self.assertEqual(len({cluster_id(c) for c in data["cases"]}), 3)
        for case in data["cases"]:
            with self.subTest(task=case["profile"]):
                self.assertNotIn("seed", case)
                validate_case(case)
                with self.assertRaises(ValueError):
                    validate_case_version(case, "2.7.0")
                corrupt = copy.deepcopy(case)
                corrupt["files"][next(iter(corrupt["files"]))] += "modified"
                with self.assertRaises(ValueError):
                    validate_case(corrupt)
                public = json.dumps(RepairEnvironment(case).contract())
                for hidden in ("upstream.patch", "fix_commit", case["base_commit"], IMAGE):
                    self.assertNotIn(hidden, public)

    def test_upstream_artifact_hunks_produce_the_exact_git_patch(self):
        for task in TASKS:
            with self.subTest(task=task), tempfile.TemporaryDirectory() as temp:
                env = RepairEnvironment(make_case(IMAGE, task))
                actions = json.loads((ROOT / task / "upstream-actions.json").read_text())
                for action in actions[:-2]:
                    self.assertEqual(env.step(action)["result"]["kind"], "edited")
                directory = Path(temp)
                for name, text in env.case["files"].items():
                    p = directory / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(text.encode())
                patchfile = ROOT / task / "upstream.patch"
                result = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", str(patchfile)],
                                        cwd=directory, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in env.changed_paths():
                    self.assertEqual((directory / name).read_bytes(), env.files[name].encode())
                self.assertTrue(env.evidence()["patch"])
                self.assertFalse(env.grade()["success"])

    def test_oracle_and_payload_bounds_cover_each_contract(self):
        sizes = {}
        for task in TASKS:
            rows = selected(task, "all")
            sizes[task] = len(rows)
            smoke = selected(task, "reproduction")
            self.assertEqual(len(smoke), 1)
            self.assertIn(smoke[0], rows)
            answers = [r["expected"] for r in rows]
            self.assertTrue(assess_rows(rows, {"status": "completed", "values": answers})["passed"])
            self.assertFalse(assess_rows(rows, {"status": "completed", "values": answers[:-1]})["passed"])
            payload = {"files": make_case(IMAGE, task)["files"], "requests": [r["input"] for r in rows]}
            self.assertLess(len(json.dumps(payload, ensure_ascii=False).encode()), 4_000_000)
        self.assertEqual(sizes, {"werkzeug_routing": 166, "attrs_preinit": 37, "urllib3_read": 126})

    def test_recorded_replay_binds_task_and_runtime_without_executing(self):
        for task in TASKS:
            case = make_case(IMAGE, task)
            class Fixture:
                def run(self, files, requests):
                    values = {digest(r["input"]): r["expected"] for r in selected(task, "all")}
                    return {"status": "completed", "values": [values[digest(q)] for q in requests]}
            actions = json.loads((ROOT / task / "upstream-actions.json").read_text())
            with patch("pomdp_bench.repair.DockerExecutor", return_value=Fixture()) as constructor:
                trace = run_episode(case, {"kind": "actions", "name": "artifact-fixture", "actions": actions}, "open", 0)
                self.assertEqual(constructor.call_args.kwargs, {"portfolio": True})
            with patch("pomdp_bench.repair.DockerExecutor", side_effect=AssertionError("No code execution")):
                self.assertTrue(replay(trace, case)["success"])
            trace["repository_evidence"]["calls"][0]["check_version"] = "wrong-task/1"
            with self.assertRaises(ValueError):
                replay(trace, case)


if __name__ == "__main__":
    unittest.main()
