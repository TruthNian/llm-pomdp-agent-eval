"""Host-side state and evidence tests; candidate execution is tested in Docker CI."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pomdp_bench.agents import validate_agent_version, validate_config
from pomdp_bench.collection import prepare_suite, read_run, resume_suite, run_suite
from pomdp_bench.evaluation import episode_record, recover_interrupted, replay, replay_environment, run_episode
from pomdp_bench.generator import digest
from pomdp_bench.repair import DATA, VERSION, RepairEnvironment, make_case, safe_path, suite
from pomdp_bench.repair_checks import assess, checks, selected_checks
from pomdp_bench.repair_runtime import DockerExecutor
from pomdp_bench.reporting import summarize
from pomdp_bench.worlds import Environment, validate_case, validate_case_version

IMAGE = "sha256:" + "0" * 64


class FixtureExecutor:
    """A response fixture, not actual candidate execution or evidence of a fix."""
    def run(self, files, requests):
        answers = {digest(row["input"]): row["expected"] for row in checks()}
        return {"status": "completed", "values": [copy.deepcopy(answers[digest(r)]) for r in requests]}


def edit_comment():
    return {"command": "edit", "target": {"path": "src/packaging/requirements.py",
            "old": "class Requirement:\n", "new": "class Requirement:\n    # fixture edit\n"}}


class RepairTaskTests(unittest.TestCase):
    def test_source_provenance_and_explicit_runtime(self):
        case = make_case(IMAGE)
        validate_case(case)
        self.assertEqual(len(case["files"]), 32)
        self.assertNotIn("seed", case)
        self.assertNotIn("upstream.patch", case["files"])
        for image in ("python:latest", "../image", "sha256:" + "g" * 64):
            with self.assertRaises(ValueError):
                make_case(image)
        case["files"]["src/packaging/requirements.py"] += "# changed"
        with self.assertRaises(ValueError):
            validate_case(case)
        with self.assertRaises(ValueError):
            validate_case_version(make_case(IMAGE), "2.6.0")
        with self.assertRaises(ValueError):
            Environment(make_case(IMAGE), "solver_assisted")

    def test_read_search_edit_limits_and_no_privileged_solution_in_request(self):
        env = RepairEnvironment(make_case(IMAGE))
        public = json.dumps({"task": env.contract(), "observation": env.observation()})
        for secret in ("5c163f5382", "upstream.patch", "image_id", "source_task_id", "file_sha256"):
            self.assertNotIn(secret, public)
        listing = env.step({"command": "list"})["result"]
        self.assertEqual(len(listing["paths"]), 32)
        result = env.step({"command": "search", "target": "__getstate__"})["result"]
        self.assertTrue(result["matches"])
        result = env.step({"command": "read", "target": {
            "path": "src/packaging/requirements.py", "start": 80, "lines": 30}})["result"]
        self.assertIn("__getstate__", result["text"])
        for name in ("../secret", "/root/auth", "C:/secret", "src/../secret", "src\\secret", "a//b"):
            self.assertFalse(safe_path(name))
        before = digest(env.files)
        for action in ({"command": "read", "target": {"path": "LICENSE", "start": True, "lines": 4}},
                       {"command": "edit", "target": {"path": "tests/test_requirements.py", "old": "a", "new": ""}},
                       {"command": "edit", "target": {"path": "src/packaging/requirements.py", "old": " ", "new": "x"}},
                       {"command": "shell", "target": "anything"}):
            self.assertEqual(env.step(action)["result"]["kind"], "invalid")
            self.assertEqual(digest(env.files), before)
        env.step(edit_comment())
        self.assertEqual(env.revision, 1)
        self.assertEqual(env.changed_paths(), ["src/packaging/requirements.py"])
        self.assertIn("+    # fixture edit", env.evidence()["patch"])

    def test_acceptance_requires_full_current_verification_and_patch(self):
        env = RepairEnvironment(make_case(IMAGE), executor=FixtureExecutor())
        env.step({"command": "test", "target": "reproduction"})
        self.assertFalse(env.grade()["verified_current_state"])
        env.step({"command": "verify"})
        self.assertTrue(env.grade()["verified_current_state"])
        env.step({"command": "finish"})
        self.assertFalse(env.grade()["success"], "Unchanged source is not a delivered patch")
        env = RepairEnvironment(make_case(IMAGE), executor=FixtureExecutor())
        env.step(edit_comment())
        env.step({"command": "verify"})
        self.assertFalse(env.grade()["success"], "Requires explicit handover")
        env.step({"command": "finish"})
        self.assertTrue(env.grade()["success"])
        env = RepairEnvironment(make_case(IMAGE), executor=FixtureExecutor())
        env.step({"command": "verify"})
        env.step(edit_comment())
        env.step({"command": "finish"})
        self.assertFalse(env.grade()["success"])

    def test_delivered_patch_applies_exactly_without_final_newline(self):
        env = RepairEnvironment(make_case(IMAGE))
        path = "src/packaging/requirements.py"
        original = env.files[path]
        env.step({"command": "edit", "target": {"path": path, "old": original,
                                                "new": original.rstrip() + "\n# no final newline"}})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / path
            source.parent.mkdir(parents=True)
            source.write_bytes(original.encode())
            patchfile = root / "delivery.patch"
            patchfile.write_bytes(env.evidence()["patch"].encode())
            result = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--", str(patchfile)], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), env.files[path].encode())

    def test_failure_spends_check_allowance_and_step_horizon_applies(self):
        class Broken:
            def run(self, *_):
                return {"status": "timeout"}
        env = RepairEnvironment(make_case(IMAGE), executor=Broken())
        for _ in range(8):
            self.assertEqual(env.step({"command": "verify"})["result"]["execution_status"], "timeout")
        self.assertEqual(env.step({"command": "verify"})["result"]["kind"], "blocked")
        self.assertEqual(env.grade()["code_execution_failures"], 8)
        while not env.done:
            env.step({"command": "list"})
        self.assertEqual(env.reason, "step_limit")
        with self.assertRaises(RuntimeError):
            env.step({"command": "finish"})

    def test_oracle_does_not_accept_process_exit_or_claimed_pass(self):
        for response in ({"status": "timeout"}, {"status": "completed", "values": {"passed": True}},
                         {"status": "completed", "values": []}):
            self.assertFalse(assess("all", response)["passed"])
        correct = {"status": "completed", "values": [r["expected"] for r in selected_checks("reproduction")]}
        self.assertTrue(assess("reproduction", correct)["passed"])
        changed = copy.deepcopy(correct)
        changed["values"][0]["raw_prereleases"] = 1
        self.assertFalse(assess("reproduction", changed)["passed"], "JSON types matter; 1 is not True")
        class Malformed:
            def run(self, *_):
                return {"status": "completed", "values": []}
        env = RepairEnvironment(make_case(IMAGE), executor=Malformed())
        env.step({"command": "verify"})
        self.assertEqual(env.grade()["code_execution_failures"], 1)


class RepairEvidenceTests(unittest.TestCase):
    def test_replay_regrades_recorded_values_and_binds_exact_code_and_image(self):
        case, snapshots = make_case(IMAGE), []
        config = {"name": "fixture", "kind": "actions",
                  "actions": [edit_comment(), {"command": "verify"}, {"command": "finish"}]}
        with patch("pomdp_bench.repair.DockerExecutor", return_value=FixtureExecutor()):
            trace = run_episode(case, config, "open", 0, checkpoint=lambda t: snapshots.append(copy.deepcopy(t)))
        with patch("pomdp_bench.repair.DockerExecutor", side_effect=AssertionError("replay must not execute")):
            self.assertTrue(replay(trace, case)["success"])
            for snapshot in snapshots:
                replay(recover_interrupted(snapshot, case), case)
        for mutation in ("files_sha256", "image_id", "input_sha256", "values", "extra", "patch"):
            corrupt = copy.deepcopy(trace)
            evidence = corrupt["repository_evidence"]
            if mutation in ("files_sha256", "image_id", "input_sha256"):
                evidence["calls"][0][mutation] = "wrong"
            elif mutation == "values":
                evidence["calls"][0]["response"]["values"][0]["name"] = "incorrect"
            elif mutation == "extra":
                evidence["calls"].append(copy.deepcopy(evidence["calls"][0]))
            else:
                evidence["patch"] = ""
            with self.assertRaises(ValueError, msg=mutation):
                replay(corrupt, case)
        with patch("pomdp_bench.repair.DockerExecutor", return_value=FixtureExecutor()) as runtime:
            replay_environment(trace, case, execute_checks=True)
            self.assertTrue(runtime.called)

    def test_shared_collector_resumes_without_redial_and_clusters_by_task(self):
        config = {"name": "fixture", "kind": "actions",
                  "actions": [edit_comment(), {"command": "verify"}, {"command": "finish"}]}
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            with patch("pomdp_bench.repair.DockerExecutor", return_value=FixtureExecutor()):
                report = run_suite(suite(IMAGE), [config], ["open"], 1, out)
            with patch("pomdp_bench.collection.run_episode", side_effect=AssertionError("must not repeat")):
                self.assertEqual(resume_suite(out), report)
            _, records = read_run(out)
            row = summarize(records)["overall"][0]
            self.assertEqual(row["task_clusters"], 1)
            self.assertNotIn("seed_clusters", row)
            self.assertIsNone(row["mean_diagnostic_cost"])
            self.assertIsNone(records[0]["clairvoyant_action_cost_lower_bound"])
            self.assertIsNone(records[0]["successful_excess_cost_over_lower_bound"])
            self.assertIn("repository_evidence", records[0])

    def test_invalid_definitions_create_no_run(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            for config, conditions in (({"name": "x", "kind": "reference"}, ["open"]),
                                        ({"name": "x", "kind": "actions", "actions": [{"command": "finish"}]},
                                         ["procedural"])):
                with self.assertRaises(ValueError):
                    prepare_suite(suite(IMAGE), [config], conditions, 1, out)
                self.assertFalse(out.exists())
        with self.assertRaises(ValueError):
            validate_config({"name": "x", "kind": "reference", "actions": []})
        with self.assertRaises(ValueError):
            validate_agent_version({"kind": "actions"}, "2.6.0")


class DockerBoundaryTests(unittest.TestCase):
    def execute(self, output=b"[]", returncode=0, timeout=False):
        class Process:
            def __init__(self):
                self.stdout, self.killed, self.waits = io.BytesIO(output), False, 0
            def wait(self, **_):
                self.waits += 1
                if timeout and self.waits == 1:
                    raise subprocess.TimeoutExpired("docker", 20)
                return returncode
            def kill(self):
                self.killed = True
            def poll(self):
                return 0
        proc = Process()
        with patch("pomdp_bench.repair_runtime.shutil.which", return_value="docker"), \
                patch("pomdp_bench.repair_runtime.subprocess.Popen", return_value=proc) as start, \
                patch("pomdp_bench.repair_runtime.subprocess.run") as cleanup:
            result = DockerExecutor(IMAGE).run({}, [])
            command = start.call_args.args[0]
            for flag in ("--network=none", "--read-only", "--cap-drop=ALL",
                         "--security-opt=no-new-privileges", "--pull=never", "--user=65534:65534"):
                self.assertIn(flag, command)
            self.assertNotIn("--mount", command)
            self.assertNotIn("-v", command)
            self.assertNotIn("-e", command)
            self.assertEqual(cleanup.call_args.args[0][:3], ["docker", "rm", "-f"])
        return result

    def test_isolation_and_bounded_outputs(self):
        self.assertEqual(self.execute(), {"status": "completed", "values": []})
        self.assertEqual(self.execute(b"PASS"), {"status": "invalid_response"})
        self.assertEqual(self.execute(b"", 1), {"status": "process_error"})
        self.assertEqual(self.execute(b"x" * 270000), {"status": "output_limit"})
        self.assertEqual(self.execute(timeout=True), {"status": "timeout"})

    def test_absent_runtime_is_explicit(self):
        with patch("pomdp_bench.repair_runtime.shutil.which", return_value=None):
            self.assertEqual(DockerExecutor(IMAGE).run({}, []), {"status": "runtime_error"})


if __name__ == "__main__":
    unittest.main()
