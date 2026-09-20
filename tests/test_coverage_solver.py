"""Ablate search while preserving public observations, action costs and replay."""
import copy
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from pomdp_bench import version_at_least
from pomdp_bench.agents import validate_agent_version
from pomdp_bench.cli import main
from pomdp_bench.collection import prepare_suite, read_run, resume_suite, run_suite
from pomdp_bench.coverage import (DEPTH_SCALES, DEPTH_VERSION, SOLVER_NODE_LIMIT, CoverageEnvironment,
                                  SearchLimit, _generate, cover_plan, generate, generate_depth, policy_action, suite)
from pomdp_bench.evaluation import recover_interrupted, replay, run_episode, validate_suite
from pomdp_bench.generator import digest, suite as diagnostic_suite
from pomdp_bench.reporting import summarize
from pomdp_bench.worlds import Environment, validate_case
from tools.export_coverage_evidence import export_run


def request(env):
    return {"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}


class DepthTests(unittest.TestCase):
    def test_qualified_stream_preserved_and_replayed_across_all_public_seeds(self):
        frozen = json.loads((Path(__file__).resolve().parents[1] /
                             "studies/coverage-qualification-v1/evidence.json").read_text(encoding="utf-8"))
        qualified = {(row["public_seed"], row["profile"]): row for row in frozen["control_rows"]
                     if row["control"] == "reference"}
        for name, shape in DEPTH_SCALES.items():
            original = "probe-" + "-".join(map(str, shape))
            for seed in range(12):
                case = generate_depth(seed, name)
                old = _generate(seed, original, shape, "dependency-cover-exploration/0")
                self.assertEqual(digest(old), qualified[seed, original]["case_sha256"])
                self.assertEqual({**case, "generator_version": old["generator_version"], "profile": original}, old)
                validate_case(case)
                for policy, condition, steps in (("cover_reference", "open", 7),
                                                  ("cover_solver", "solver_assisted", 9)):
                    trace = run_episode(case, {"name": policy, "kind": policy}, condition, 0)
                    self.assertTrue(replay(trace, case)["success"], (name, seed, condition))
                    self.assertEqual(trace["grade"]["steps"], steps)
                    self.assertEqual(trace["grade"]["cost"], case["budget"])
                    if condition == "solver_assisted":
                        self.assertEqual(trace["grade"]["solver_calls"], 2)
                        self.assertEqual(trace["grade"]["solver_limit_failures"], 0)
                        searches = [e["observation"]["result"] for e in trace["events"]
                                    if e["action"]["command"] == "solve"]
                        for actual, expected in zip(searches, qualified[seed, original]["searches"], strict=True):
                            self.assertEqual(actual["search_states"], expected["states"])
                            self.assertEqual(digest(actual["plan"]), expected["plan_sha256"])

    def test_explicit_profile_and_version_gates(self):
        for kwargs in ({"profiles": ["depth18"]}, {"profiles": ["hard"], "experimental": True},
                       {"profiles": ["probe-96-4-384"], "experimental": True}):
            with self.assertRaises(ValueError):
                suite([0], **kwargs)
        mixed = suite([0], experimental=True)
        mixed["cases"].append(generate(0))
        with self.assertRaises(ValueError):
            validate_suite(mixed)
        for case, condition in ((generate_depth(0), "open"), (generate(0), "solver_assisted")):
            with self.assertRaises(ValueError):
                Environment(case, condition, framework_version="2.5.3")
        with self.assertRaises(ValueError):
            validate_agent_version({"kind": "cover_solver"}, "2.5.3")
        self.assertFalse(version_at_least("999.0.0", "2.6.0"))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "suite.json"
            with self.assertRaises(SystemExit):
                main(["generate-cover", "--scales", "depth24", "--out", str(output)])
            self.assertFalse(output.exists())
            self.assertEqual(main(["generate-cover", "--experimental", "--count", "1", "--scales",
                                   "depth24", "--out", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["generator_version"], DEPTH_VERSION)


class SolverTransitionTests(unittest.TestCase):
    def test_only_revealed_rows_reach_solver_no_hidden_answers_or_automatic_work(self):
        env = CoverageEnvironment(generate(0, "hard"), "solver_assisted")
        other = CoverageEnvironment(generate(0, "hard"), "solver_assisted")
        # Unknown current and future rows differ, yet cannot affect this action.
        other.case["epochs"] = [{name: [] for name in env.case["operations"]}] * 2
        before = env.observation()
        with patch("pomdp_bench.coverage.cover_plan", wraps=cover_plan) as search:
            a = env.step({"command": "solve"})
            search.assert_called_once_with({}, set(before["goals"]), before["work_remaining"],
                                           node_limit=SOLVER_NODE_LIMIT)
        self.assertEqual(a, other.step({"command": "solve"}))
        self.assertEqual(a["result"]["status"], "no_plan_in_revealed_catalogue")
        self.assertEqual(env.spent, 0)
        self.assertEqual(env.work, 0)
        self.assertFalse(env.covered)
        self.assertFalse(env.grade()["verified_current_state"])
        env.step({"command": "probe", "target": "all"})
        with patch("pomdp_bench.coverage.cover_plan", wraps=cover_plan) as search:
            result = env.step({"command": "solve"})["result"]
            self.assertEqual(search.call_args.args[0], env.catalogue)
        self.assertEqual(result["status"], "found")
        self.assertTrue(set().union(*(set(env.catalogue[n]) for n in result["plan"])) >= set(env.case["goals"]))
        self.assertEqual(env.work, 0)
        self.assertFalse(env.grade()["success"])

    def test_schema_quota_and_exhaustion_do_not_fabricate_infeasibility(self):
        env = CoverageEnvironment(generate(0, "sanity", recovery=False), "solver_assisted")
        self.assertEqual(env.step({"command": "solve", "target": "all"})["result"]["kind"], "invalid")
        self.assertEqual(env.metrics["solver_calls"], 0)
        with patch("pomdp_bench.coverage.cover_plan", side_effect=SearchLimit(SOLVER_NODE_LIMIT + 1)):
            result = env.step({"command": "solve"})["result"]
        self.assertEqual(result, {"kind": "solve", "status": "search_limit", "plan": None,
                                  "revision": 0, "search_states": SOLVER_NODE_LIMIT + 1})
        with patch("pomdp_bench.coverage.cover_plan", side_effect=AssertionError("quota exhausted")):
            self.assertEqual(env.step({"command": "solve"})["result"]["kind"], "blocked")
        self.assertEqual(env.metrics["solver_calls"], 1)
        self.assertEqual(env.metrics["solver_limit_failures"], 1)
        self.assertEqual(env.metrics["solver_search_states"], SOLVER_NODE_LIMIT + 1)
        self.assertEqual(len(env.history), 3)
        self.assertEqual(env.spent, 0)

    def test_quota_does_not_refill_and_hints_do_not_survive_changed_state(self):
        env = CoverageEnvironment(generate(0, "sanity"), "solver_assisted")
        for _ in range(3):
            env.step(policy_action("cover_solver", request(env)))
        old_plan = env.history[1]["observation"]["result"]
        env.step({"command": "verify"})
        self.assertNotEqual(old_plan["revision"], env.revision)
        self.assertEqual(env.observation()["solver_calls_remaining"], 1)
        self.assertEqual(env.catalogue, {})
        self.assertEqual(env.step({"command": "build", "target": old_plan["plan"]})["result"]["kind"], "invalid")
        # Solver has no implicit re-probe after external change.
        self.assertEqual(env.step({"command": "solve"})["result"]["status"], "no_plan_in_revealed_catalogue")
        env.step({"command": "finish"})
        self.assertFalse(env.grade()["success"])

    def test_open_stays_identical_to_2_5_3_and_cannot_invoke_solver(self):
        case = generate(1, "sanity")
        a, b = CoverageEnvironment(case), CoverageEnvironment(case, framework_version="2.5.3")
        self.assertEqual(a.contract(), b.contract())
        self.assertNotIn("solver", a.contract())
        self.assertEqual(a.step({"command": "solve"}), b.step({"command": "solve"}))
        while not a.done:
            action = policy_action("cover_reference", request(a))
            self.assertEqual(a.step(action), b.step(action))
        self.assertEqual(a.grade(), b.grade())
        self.assertNotIn("solver_calls", a.grade())

    def test_solver_policy_has_no_independent_search_and_preserves_finish_gate(self):
        for recovery, steps in ((True, 9), (False, 5)):
            env = CoverageEnvironment(generate(1, "sanity", recovery=recovery), "solver_assisted")
            while not env.done:
                with patch("pomdp_bench.coverage.cover_plan", side_effect=AssertionError("policy must use action")):
                    action = policy_action("cover_solver", request(env))
                if action["command"] == "finish":
                    self.assertFalse(env.grade()["success"])
                env.step(action)
            self.assertTrue(env.grade()["success"])
            self.assertEqual(len(env.history), steps)


class SolverCollectionTests(unittest.TestCase):
    def test_bad_combinations_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            for data, kind, conditions in ((suite([0]), "cover_solver", ["open", "solver_assisted"]),
                                           (diagnostic_suite([0]), "reference", ["solver_assisted"])):
                with self.assertRaises(ValueError):
                    prepare_suite(data, [{"name": "x", "kind": kind}], conditions, 1, out)
                self.assertFalse(out.exists())

    def test_replay_and_interruption_around_solver_never_redial(self):
        case, snapshots = generate(1, "sanity"), []
        trace = run_episode(case, {"name": "tool", "kind": "cover_solver"}, "solver_assisted", 0,
                            checkpoint=lambda row: snapshots.append(copy.deepcopy(row)))
        for snapshot in snapshots:
            interrupted = recover_interrupted(snapshot, case)
            replay(interrupted, case)
        for field in ("solver_calls_remaining", "result"):
            broken = copy.deepcopy(trace)
            if field == "result":
                broken["events"][1]["observation"][field]["plan"] = []
            else:
                broken["events"][1]["observation"][field] += 1
            with self.assertRaises(ValueError):
                replay(broken, case)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            run_suite(suite([0], ["sanity"]), [{"name": "tool", "kind": "cover_solver"}],
                      ["solver_assisted"], 1, out)
            with patch("pomdp_bench.collection.run_episode", side_effect=AssertionError("no repeats")):
                resume_suite(out)

    def test_http_environment_action_and_export_keep_conditions_and_public_hashes(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                public = json.loads(body["messages"][1]["content"])
                requests.append(public)
                kind = "cover_solver" if "solver" in public["task"] else "cover_reference"
                action = policy_action(kind, public)
                raw = json.dumps({"choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(action)}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"name": "fixture", "kind": "chat", "model": "fixture",
                  "endpoint_env": "SOLVER_TEST_ENDPOINT", "api_key_env": "SOLVER_TEST_KEY"}
        try:
            with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
                    "SOLVER_TEST_ENDPOINT": f"http://127.0.0.1:{server.server_port}/chat",
                    "SOLVER_TEST_KEY": "fixture-only"}):
                out = Path(temp) / "run"
                run_suite(suite([0], ["sanity"]), [config], ["open", "solver_assisted"], 1, out)
                evidence = export_run(out)
                self.assertTrue(evidence["source_matches_export_checkout"])
                self.assertEqual({r["condition"] for r in evidence["outcomes"]}, {"open", "solver_assisted"})
                _, records = read_run(out)
                report = summarize(records)
                self.assertFalse(report["solver_assistance"][0]["compute_matched"])
                self.assertIsNone(report["solver_assistance"][0]["cluster_bootstrap95"])
                self.assertEqual(report["prompt_rescue"], [])
                for row in report["overall"]:
                    if row["condition"] == "solver_assisted":
                        self.assertEqual(row["mean_solver_calls"], 2)
                    else:
                        self.assertNotIn("mean_solver_calls", row)
                    self.assertIsNone(row["total_output_tokens"])
            self.assertEqual(len(requests), 16)
            for forbidden in ('"seed"', '"epochs"', '"profile"', '"changed_goals"', '"case_id"'):
                self.assertNotIn(forbidden, json.dumps(requests))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
