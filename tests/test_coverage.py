from __future__ import annotations

import copy
import itertools
import json
import os
import random
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from pomdp_bench import __version__
from pomdp_bench.cli import main
from pomdp_bench.collection import prepare_suite, resume_suite, read_run, run_suite
from pomdp_bench.coverage import CoverageEnvironment, POLICIES, SCALES, cover_plan, generate, policy_action, suite
from pomdp_bench.evaluation import episode_record, run_episode, replay, recover_interrupted, validate_suite
from pomdp_bench.generator import suite as diagnostic_suite
from pomdp_bench.reporting import summarize
from pomdp_bench.worlds import validate_case


def request(env):
    return {"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}


class CoveragePlanningTests(unittest.TestCase):
    def test_exact_public_search_matches_independent_bruteforce(self):
        rng = random.Random(44)
        for _ in range(150):
            goals = {str(i) for i in range(rng.randint(1, 7))}
            rows = {str(i): rng.sample(sorted(goals), rng.randint(1, len(goals))) for i in range(8)}
            limit = rng.randrange(5)
            best = next((size for size in range(limit + 1) for names in itertools.combinations(rows, size)
                         if set().union(*(set(rows[n]) for n in names)) >= goals), None)
            plan, _ = cover_plan(rows, goals, limit)
            self.assertEqual(len(plan) if plan is not None else None, best)
            if plan:
                self.assertTrue(set().union(*(set(rows[n]) for n in plan)) >= goals)

    def test_search_exhaustion_is_not_misreported_as_no_solution(self):
        with self.assertRaisesRegex(RuntimeError, "search limit"):
            cover_plan({"a": ["x"]}, {"x"}, 1, node_limit=0)

    def test_constructive_reference_solves_all_scales_and_replays(self):
        for seed in range(12):
            for scale in SCALES:
                case = generate(seed, scale)
                trace = run_episode(case, {"name": "reference", "kind": "cover_reference"}, "open", 0)
                self.assertTrue(trace["grade"]["success"], (seed, scale, trace["error"]))
                self.assertEqual(replay(trace, case), trace["grade"])
                self.assertEqual(trace["grade"]["work_spent"], sum(case["work_limits"]))
                self.assertEqual(trace["grade"]["cost"], case["budget"])
                self.assertEqual(trace["grade"]["steps"], 7)

    def test_budget_does_not_reveal_sampled_graph_or_changed_goal_identity(self):
        for scale in SCALES:
            contracts = [CoverageEnvironment(generate(seed, scale)).contract() for seed in range(10)]
            self.assertTrue(all(c == contracts[0] for c in contracts))
        self.assertNotEqual(generate(1, "hard")["epochs"], generate(2, "hard")["epochs"])

    def test_local_heuristics_fail_and_relaxed_resources_rescue_them(self):
        for policy in ("cover_greedy", "cover_rarest"):
            strict = generate(0, "hard")
            relaxed = generate(0, "hard", slack=32)
            self.assertEqual(strict["epochs"], relaxed["epochs"])
            config = {"name": policy, "kind": policy}
            self.assertFalse(run_episode(strict, config, "open", 0)["grade"]["success"])
            self.assertTrue(run_episode(relaxed, config, "open", 0)["grade"]["success"])

    def test_recovery_ablation_rescues_policy_without_revision(self):
        config = {"name": "frozen", "kind": "cover_no_recovery"}
        for scale in SCALES:
            a, b = generate(3, scale), generate(3, scale, recovery=False)
            self.assertEqual(a["epochs"][0], b["epochs"][0])
            self.assertFalse(run_episode(a, config, "open", 0)["grade"]["success"])
            self.assertTrue(run_episode(b, config, "open", 0)["grade"]["success"])

    def test_generation_validation_and_one_generator_per_suite(self):
        a = generate(3)
        self.assertEqual(a, generate(3))
        a["work_limits"][0] += 1
        with self.assertRaises(ValueError):
            validate_case(a)
        mixed = suite([0])
        mixed["cases"].extend(diagnostic_suite([0])["cases"])
        with self.assertRaises(ValueError):
            validate_suite(mixed)
        for kwargs in ({"seed": True}, {"seed": -1}, {"seed": 0, "slack": -1},
                       {"seed": 0, "slack": 100}, {"seed": 0, "recovery": "yes"}):
            with self.assertRaises(ValueError):
                generate(**kwargs)


class CoverageTransitionTests(unittest.TestCase):
    def test_no_future_matrix_or_seed_in_public_request(self):
        env = CoverageEnvironment(generate(0))
        self.assertEqual(env.observation()["catalogue"], {})
        for forbidden in ("seed", "epochs", "changed_goals", "case_id", "profile", "generator_version"):
            self.assertNotIn(forbidden, str(request(env)))
        other = copy.deepcopy(env.case)
        other["epochs"][1] = {k: list(reversed(v)) for k, v in other["epochs"][1].items()}
        b = CoverageEnvironment(other)
        for _ in range(2):
            action = policy_action("cover_reference", request(env))
            self.assertEqual(env.step(action), b.step(action))
        self.assertEqual(env.step({"command": "verify"}), b.step({"command": "verify"}))

    def test_change_preserves_unaffected_work_but_invalidates_evidence_and_pass(self):
        env = CoverageEnvironment(generate(0, "sanity"))
        env.step(policy_action("cover_reference", request(env)))
        env.step(policy_action("cover_reference", request(env)))
        old_catalogue = copy.deepcopy(env.catalogue)
        old_cost = env.spent
        obs = env.step({"command": "verify"})
        self.assertTrue(obs["result"]["passed"])
        self.assertNotEqual(obs["result"]["checked_revision"], obs["revision"])
        self.assertEqual(set(obs["covered"]), set(env.case["goals"]) - set(env.case["changed_goals"]))
        self.assertEqual(obs["catalogue"], {})
        self.assertEqual(env.spent, old_cost + 1)
        self.assertFalse(env.grade()["verified_current_state"])
        self.assertEqual(env.step({"command": "build", "target": [next(iter(old_catalogue))]})["result"]["kind"], "invalid")
        env.step({"command": "finish"})
        self.assertFalse(env.grade()["success"])

    def test_batch_is_atomic_and_charged_per_member(self):
        env = CoverageEnvironment(generate(0, "sanity", recovery=False))
        name = env.case["operations"][0]
        self.assertEqual(env.step({"command": "build", "target": [name]})["result"]["kind"], "invalid")
        env.step({"command": "probe", "target": "all"})
        spent = env.spent
        for targets in ([name, "not-known"], [name, name], [], [None], env.case["operations"]):
            env.step({"command": "build", "target": targets})
            self.assertEqual(env.spent, spent)
            self.assertFalse(env.covered)
        names = env.case["operations"][:2]
        env.step({"command": "build", "target": names})
        self.assertEqual(env.work, 2)
        self.assertEqual(env.spent, spent + 2)
        self.assertEqual(env.covered, set(env.catalogue[names[0]]) | set(env.catalogue[names[1]]))

    def test_scalar_actions_schema_and_repeated_mutation(self):
        env = CoverageEnvironment(generate(0, "sanity", recovery=False, slack=1))
        for action in ({"command": []}, {"command": "probe", "target": []}, {"command": "status", "extra": 1}):
            self.assertEqual(env.step(action)["result"]["kind"], "invalid")
        for _ in range(3):
            env.step(policy_action("cover_reference", request(env)))
        self.assertTrue(env.grade()["verified_current_state"])
        env.step({"command": "build", "target": [next(iter(env.catalogue))]})
        self.assertFalse(env.grade()["verified_current_state"])

    def test_free_actions_cannot_evade_horizon_or_explicit_finish(self):
        env = CoverageEnvironment(generate(0, "sanity", recovery=False))
        for _ in range(3):
            env.step(policy_action("cover_reference", request(env)))
        self.assertFalse(env.grade()["success"])
        while len(env.history) < env.case["max_steps"] - 1:
            env.step({"command": "status"})
        env.step({"command": "finish"})
        self.assertTrue(env.grade()["success"])
        with self.assertRaises(RuntimeError):
            env.step({"command": "status"})
        other = CoverageEnvironment(generate(0, "sanity"))
        for _ in range(other.case["max_steps"]):
            other.step({"command": "status"})
        self.assertEqual(other.grade()["termination"], "step_limit")

    def test_public_contract_cannot_mutate_work_allowance(self):
        env = CoverageEnvironment(generate(0))
        before = env.case["work_limits"][:]
        env.contract()["work_limits"][0] = 999
        self.assertEqual(env.case["work_limits"], before)


class CoverageCollectionTests(unittest.TestCase):
    def test_legacy_action_contract_and_invalid_feedback_replay_unchanged(self):
        case = generate(0, "sanity")
        env = CoverageEnvironment(case, framework_version="2.5.0")
        env.step({"action": "probe", "target": "all"})
        self.assertEqual(env.observation()["result"], {"kind": "invalid"})
        self.assertNotIn("response_format", env.contract())
        while not env.done:
            env.step(policy_action("cover_reference", request(env)))
        trace = episode_record(env, {"name": "ref", "kind": "reference"}, 0)
        trace["framework_version"] = "2.5.0"
        self.assertTrue(replay(trace, case)["success"])
        current = CoverageEnvironment(case)
        self.assertIn("response_format", current.contract())
        self.assertIn("message", current.step({"action": "probe", "target": "all"})["result"])
        trace["framework_version"] = __version__
        with self.assertRaises(ValueError):
            replay(trace, case)

    def test_http_adapter_supports_public_multiturn_batch_actions(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                public = json.loads(body["messages"][1]["content"])
                requests.append(public)
                action = policy_action("cover_reference", public)
                payload = {"choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(action)}}]}
                raw = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"name": "fixture", "kind": "chat", "model": "fixture", "endpoint_env": "COVER_TEST_ENDPOINT",
                  "api_key_env": "COVER_TEST_KEY"}
        try:
            with patch.dict(os.environ, {"COVER_TEST_ENDPOINT": f"http://127.0.0.1:{server.server_port}/chat",
                                         "COVER_TEST_KEY": "fixture-only"}):
                case = generate(1, "hard")
                trace = run_episode(case, config, "open", 0)
            self.assertTrue(replay(trace, case)["success"])
            self.assertEqual(len(requests), 7)
            self.assertIsInstance(trace["events"][1]["action"]["target"], list)
            self.assertTrue(all(set(r) == {"protocol_version", "task", "observation", "history"} for r in requests))
            self.assertNotIn('"epochs"', json.dumps(requests))
            self.assertNotIn('"seed"', json.dumps(requests))
            self.assertEqual(trace["usage"]["requests_with_usage"], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_shared_collector_resume_and_nonapplicable_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            prepare_suite(suite([0], ["sanity", "hard"]),
                          [{"name": p, "kind": p} for p in POLICIES], ["open"], 1, out)
            report = resume_suite(out)
            self.assertEqual(report["episodes"], 8)
            with patch("pomdp_bench.collection.run_episode", side_effect=AssertionError("must not redial")):
                self.assertEqual(resume_suite(out), report)
            _, records = read_run(out)
            self.assertTrue(all(r["framework_version"] == __version__ for r in records))
            for row in report["overall"]:
                self.assertIsNone(row["mean_diagnostic_cost"])
                self.assertIsNone(row["wrong_repair_rate"])
                self.assertIsNotNone(row["mean_work_spent"])

    def test_interrupted_episode_and_replay_tampering(self):
        case = generate(0, "sanity")
        snapshots = []
        trace = run_episode(case, {"name": "ref", "kind": "reference"}, "open", 0,
                            checkpoint=lambda t: snapshots.append(copy.deepcopy(t)))
        interrupted = recover_interrupted(snapshots[2], case)
        self.assertEqual(interrupted["grade"]["termination"], "collection_interrupted")
        self.assertFalse(interrupted["grade"]["success"])
        replay(interrupted, case)
        for field in ("observation", "grade", "version"):
            broken = copy.deepcopy(trace)
            if field == "observation":
                broken["events"][0]["observation"]["work_remaining"] += 1
            elif field == "grade":
                broken["grade"]["success"] = False
            else:
                broken["framework_version"] = "2.4.0"
            with self.assertRaises(ValueError):
                replay(broken, case)

    def test_wrong_conditions_and_cross_family_policies_fail_before_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            for data, kind, conditions in ((suite([0]), "reference", ["procedural"]),
                                            (suite([0]), "proxy", ["open"]),
                                            (diagnostic_suite([0]), "cover_reference", ["open"])):
                with self.assertRaises(ValueError):
                    prepare_suite(data, [{"name": "x", "kind": kind}], conditions, 1, out)
                self.assertFalse(out.exists())

    def test_cli_roundtrip_and_unknown_usage_remains_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            spec, out = Path(temp) / "suite.json", Path(temp) / "run"
            self.assertEqual(main(["generate-cover", "--count", "1", "--scales", "sanity", "--out", str(spec)]), 0)
            self.assertEqual(main(["run", "--suite", str(spec), "--out", str(out)]), 0)
            self.assertEqual(main(["validate", str(out)]), 0)
            _, records = read_run(out)
            self.assertIsNone(summarize(records)["overall"][0]["total_input_tokens"])


if __name__ == "__main__":
    unittest.main()
