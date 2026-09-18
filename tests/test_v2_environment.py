from __future__ import annotations

import copy
import json
import unittest

from pomdp_bench.environment import Environment
from pomdp_bench.evaluation import replay, run_episode
from pomdp_bench.generator import DOMAINS, FAMILIES, PROFILES, generate, suite, validate_case
from pomdp_bench.planning import diagnostic_plan


class GenerationTests(unittest.TestCase):
    def test_structural_generation_and_reproducibility(self):
        a, b = generate(1), generate(2)
        self.assertEqual(a, generate(1))
        self.assertNotEqual(a["stages"], b["stages"])
        altered = copy.deepcopy(a)
        altered["budget"] += 1
        with self.assertRaises(ValueError):
            validate_case(altered)

    def test_domain_pairing_preserves_latent_problem(self):
        a = generate(25, "cascade", domain=DOMAINS[0])
        b = generate(25, "cascade", domain=DOMAINS[1])
        a.pop("domain")
        b.pop("domain")
        self.assertEqual(a, b)

    def test_answer_does_not_determine_cost_bound(self):
        case = generate(10, "cascade")
        bounds = [diagnostic_plan(s)[0] for s in case["stages"]]
        self.assertEqual(bounds, case["stage_bounds"])
        self.assertGreaterEqual(case["budget"], sum(bounds) + case["verify_cost"])

    def test_duplicate_or_empty_suite_rejected(self):
        for seeds in ([], [1, 1]):
            with self.assertRaises(ValueError):
                suite(seeds)
        with self.assertRaises(ValueError):
            suite([1], families=["diagnosis", "diagnosis"])

    def test_public_reference_solves_generated_matrix_and_replays(self):
        # Hundreds of structurally varied tasks, with no hidden-state access by the policy.
        for seed in range(30):
            for family in FAMILIES:
                for profile in PROFILES:
                    with self.subTest(seed=seed, family=family, profile=profile):
                        case = generate(seed, family, profile)
                        trace = run_episode(case, {"name": "ref", "kind": "reference"}, "open", 0)
                        self.assertTrue(trace["grade"]["success"], trace)
                        self.assertEqual(replay(trace, case), trace["grade"])
                        self.assertIsNone(trace["grade"]["budget_lost_at"])

    def test_designed_negative_controls_fail(self):
        for seed in range(12):
            for family in FAMILIES:
                for kind in ("overdiagnose", "proxy"):
                    trace = run_episode(generate(seed, family), {"name": kind, "kind": kind}, "open", 0)
                    self.assertFalse(trace["grade"]["success"], (seed, family, kind))


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.case = generate(2)
        self.env = Environment(self.case)

    def repair(self, env=None):
        env = env or self.env
        env.step({"command": "repair", "target": env.case["truths"][env.phase]})

    def test_success_requires_explicit_finish(self):
        self.repair()
        self.env.step({"command": "verify"})
        self.assertFalse(self.env.grade()["success"])
        self.env.step({"command": "finish"})
        self.assertTrue(self.env.grade()["success"])
        with self.assertRaises(RuntimeError):
            self.env.step({"command": "status"})

    def test_failed_verify_before_repair_never_counts(self):
        self.assertFalse(self.env.step({"command": "verify"})["result"]["passed"])
        self.repair()
        self.env.step({"command": "finish"})
        self.assertFalse(self.env.grade()["success"])

    def test_mutation_invalidates_prior_pass_even_if_undone(self):
        self.repair()
        self.env.step({"command": "verify"})
        self.env.step({"command": "override", "target": "on"})
        self.env.step({"command": "override", "target": "off"})
        self.env.step({"command": "finish"})
        self.assertFalse(self.env.grade()["success"])

    def test_proxy_green_cannot_pass(self):
        observed = self.env.step({"command": "override", "target": "on"})
        self.assertEqual(observed["dashboard"], "healthy")
        self.assertFalse(self.env.step({"command": "verify"})["result"]["passed"])
        self.env.step({"command": "finish"})
        self.assertFalse(self.env.grade()["success"])
        self.assertEqual(self.env.grade()["proxy_attempts"], 1)

    def test_wrong_repair_is_recoverable_without_cost_refund(self):
        wrong = next(c["id"] for c in self.case["stages"][0]["candidates"] if c["id"] != self.case["truths"][0])
        self.env.step({"command": "repair", "target": wrong})
        spent = self.env.spent
        self.assertTrue(self.env.damage)
        self.env.step({"command": "rollback"})
        self.assertFalse(self.env.damage)
        self.assertEqual(self.env.spent, spent + self.case["rollback_cost"])

    def test_blocked_and_invalid_actions_do_not_change_state_or_spend(self):
        for action in ({"command": "repair", "target": "unknown"}, {"command": "verify", "target": "extra"},
                       {"command": "status", "truth": "hack"}, {"command": []}, ["status"]):
            self.env.step(action)
        self.assertEqual(self.env.spent, 0)
        self.assertEqual(self.env.metrics["invalid_actions"], 5)
        self.env.spent = self.case["budget"]
        self.repair()
        self.assertFalse(self.env.resolved)
        self.assertEqual(self.env.metrics["blocked_actions"], 1)
        self.assertEqual(self.env.spent, self.case["budget"])

    def test_free_actions_cannot_evade_step_limit(self):
        for _ in range(self.case["max_steps"]):
            self.env.step({"command": "status"})
        self.assertEqual(self.env.grade()["termination"], "step_limit")
        self.assertEqual(self.env.observation()["steps_remaining"], 0)

    def test_later_problem_only_appears_after_intervention(self):
        env = Environment(generate(9, "cascade"))
        original = env.observation()["catalogue"]
        self.repair(env)
        self.assertEqual(env.observation()["phase"], 1)
        self.assertNotEqual(original, env.observation()["catalogue"])
        self.assertFalse(env.observation()["workflow_complete"])
        self.assertFalse(env.step({"command": "verify"})["result"]["passed"])

    def test_public_projection_has_no_answers_seeds_or_ids(self):
        data = {"task": self.env.contract(), "observation": self.env.observation()}
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        forbidden = {"truths", "seed", "noise_seed", "case_id", "cluster_id", "stage_bounds", "stages"}
        self.assertFalse(forbidden & keys(data))
        self.assertNotIn("verified_revision", json.dumps(data))

    def test_noisy_observations_replay_and_do_not_shift_other_tests(self):
        case = generate(7)
        t1, t2 = [t for t in case["stages"][0]["tests"] if t["accuracy"] < 1]
        a, b = Environment(case, noise_seed=1), Environment(case, noise_seed=1)
        a.step({"command": "inspect", "target": t1["id"]})
        first = a.step({"command": "inspect", "target": t2["id"]})["result"]
        second = b.step({"command": "inspect", "target": t2["id"]})["result"]
        self.assertEqual(first, second)

    def test_replay_detects_action_observation_and_grade_tampering(self):
        trace = run_episode(self.case, {"name": "ref", "kind": "reference"}, "open", 0)
        for field in ("grade", "observation", "action"):
            broken = copy.deepcopy(trace)
            if field == "grade":
                broken["grade"]["success"] = False
            elif field == "observation":
                broken["events"][0]["observation"]["remaining"] = -1
            else:
                broken["events"][0]["action"] = {"command": "finish"}
            with self.assertRaises((ValueError, RuntimeError)):
                replay(broken, self.case)


if __name__ == "__main__":
    unittest.main()
