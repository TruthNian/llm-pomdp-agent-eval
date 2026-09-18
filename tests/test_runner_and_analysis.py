from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

from analyze_results import exact_paired_two_sided, wilson  # noqa: E402
from run_incident_eval import build_specs, parse_model_specs  # noqa: E402


class RunnerTests(unittest.TestCase):
    def test_default_factorial_design_has_72_specs(self) -> None:
        specs = build_specs(
            replicates=3,
            conditions=("open", "explicit", "procedural"),
            model_keys=("gpt", "glm"),
        )

        self.assertEqual(len(specs), 72)
        self.assertEqual(len({spec.run_id for spec in specs}), 72)

    def test_model_overrides_are_applied(self) -> None:
        models = parse_model_specs(["gpt=provider/a", "candidate=provider/c"])

        self.assertEqual(models["gpt"], "provider/a")
        self.assertEqual(models["candidate"], "provider/c")

    def test_unsafe_model_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_model_specs(["../escape=provider/model"])


class AnalysisTests(unittest.TestCase):
    def test_exact_paired_result_matches_open_condition(self) -> None:
        self.assertEqual(exact_paired_two_sided(9, 0), 0.00390625)

    def test_wilson_interval_contains_observed_rate(self) -> None:
        low, high = wilson(3, 12)

        self.assertLess(low, 0.25)
        self.assertGreater(high, 0.25)


if __name__ == "__main__":
    unittest.main()
