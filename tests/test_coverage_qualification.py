import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("coverage_qualification", ROOT / "studies/coverage-qualification-v1/qualify.py")
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)


def small_plan():
    plan = json.loads((ROOT / "studies/coverage-qualification-v1/plan.json").read_text(encoding="utf-8"))
    plan.update(shapes=[[6, 2, 9]], public_seeds=[0, 1], expected_cases=2, expected_control_rows=14)
    return plan


class QualificationTests(unittest.TestCase):
    def test_complete_recovery_and_rescue_controls_replay(self):
        report = qualification.qualify(small_plan())
        self.assertEqual(len(report["control_rows"]), 14)
        for row in report["control_rows"]:
            self.assertTrue(row["replay_verified"])
            if row["control"] in ("reference", "greedy_relaxed", "rarest_relaxed", "no_recovery_stable"):
                self.assertTrue(row["grade"]["success"], row)
            if row["control"] == "no_recovery":
                self.assertFalse(row["grade"]["success"])
                self.assertEqual(row["grade"]["termination"], "finished")
        self.assertFalse(report["summaries"][0]["model_discrimination_established"])

    def test_exhaustion_keeps_unavailable_controls_explicit_and_fails_gate(self):
        plan = small_plan()
        plan["node_limit_per_reference_decision"] = 1
        report = qualification.qualify(plan)
        self.assertEqual(len(report["control_rows"]), 14)
        for row in report["control_rows"]:
            if row["control"] == "reference":
                self.assertEqual(row["grade"]["termination"], "reference_search_limit")
                self.assertEqual(row["searches"][0]["states_lower_bound"], 2)
                self.assertIsNone(row["searches"][0]["states"])
            elif row["control"].startswith("no_recovery"):
                self.assertIsNone(row["grade"])
                self.assertEqual(row["not_executed_reason"], "initial_reference_plan_unavailable")
            else:
                self.assertIsNotNone(row["grade"])
        self.assertFalse(report["summaries"][0]["offline_gate_passed"])

    def test_bad_matrix_is_rejected_before_execution(self):
        plan = small_plan()
        for field, value in (("expected_control_rows", 13), ("public_seeds", [0, 0]),
                             ("shapes", [[6, 4, 9]]), ("node_limit_per_reference_decision", True)):
            broken = copy.deepcopy(plan)
            broken[field] = value
            with self.assertRaises(ValueError):
                qualification.validate_plan(broken)

    def test_recovery_search_failure_preserves_the_initial_solution(self):
        case = qualification.coverage._generate(0, "probe-6-2-9", (6, 2, 9),
                                                "dependency-cover-exploration/0")
        original = qualification.coverage.cover_plan
        calls = 0

        def fail_recovery(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Public reference search limit reached; no infeasibility claim")
            return original(*args, **kwargs)

        with patch.object(qualification.coverage, "cover_plan", side_effect=fail_recovery):
            row, initial = qualification.evaluate(case, "reference", 1000)
        self.assertIsNotNone(initial)
        self.assertEqual(row["grade"]["termination"], "reference_search_limit")
        self.assertEqual([s["outcome"] for s in row["searches"]], ["found", "search_limit"])
        stable = qualification.coverage._generate(0, "probe-6-2-9", (6, 2, 9),
                                                  "dependency-cover-exploration/0", recovery=False)
        rescued, _ = qualification.evaluate(stable, "no_recovery_stable", 1000, initial)
        self.assertTrue(rescued["grade"]["success"])
