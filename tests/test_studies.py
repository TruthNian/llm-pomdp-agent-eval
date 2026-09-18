"""Counterexamples for experimental identification, pairing, precision and censoring."""
from __future__ import annotations

import copy
import itertools
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from pomdp_bench.agents import validate_config
from pomdp_bench.cli import main
from pomdp_bench.collection import prepare_suite, resume_suite, schedule
from pomdp_bench.environment import Environment, PROMPTS
from pomdp_bench.evaluation import replay, run_episode
from pomdp_bench.generator import FAMILIES, PROFILES, digest, generate, suite
from pomdp_bench.interventions import CONTROL, CONTRAST, NEUTRAL_TEXT, RESERVE_TEXT, TREATMENT
from pomdp_bench.reporting import validate_run
from pomdp_bench.storage import read_json, write_json
from pomdp_bench.studies import analyze_study, bind_plan, prepare_study, required_seeds, validate_plan

ROOT = Path(__file__).resolve().parents[1]


def example_plan():
    plan = read_json(ROOT / "examples" / "study-reserve.pilot.json")
    plan["independent_seeds"] = 2
    plan["task_distribution"]["families"] = ["diagnosis"]
    plan["agents"] = [{"name": "reference", "kind": "reference"}]
    return plan


def analytical_fixture(plan):
    data = suite(list(range(plan["independent_seeds"])), **plan["task_distribution"])
    records = [run_episode(c, agent, cond, rep) for c in data["cases"] for agent in plan["agents"]
               for rep in range(plan["replicates"]) for cond in CONTRAST]
    return {"study": bind_plan(plan), "cases": data["cases"]}, records


class InterventionTests(unittest.TestCase):
    def test_arms_change_only_the_frozen_task_sentence(self):
        case = generate(31, "cascade")
        a, b = Environment(case, CONTROL), Environment(case, TREATMENT)
        self.assertEqual(a.observation(), b.observation())
        ca, cb = a.contract(), b.contract()
        ca.pop("task"); cb.pop("task")
        self.assertEqual(ca, cb)
        self.assertEqual(PROMPTS[CONTROL], PROMPTS["open"] + " " + NEUTRAL_TEXT)
        self.assertEqual(PROMPTS[TREATMENT], PROMPTS["open"] + " " + RESERVE_TEXT)
        self.assertEqual(len(NEUTRAL_TEXT.split()), len(RESERVE_TEXT.split()))
        self.assertEqual(len(RESERVE_TEXT.split()), 15)

    def test_public_controls_distinguish_budget_omission_across_structures(self):
        for seed, family, profile in itertools.product(range(16), FAMILIES, PROFILES):
            case = generate(seed, family, profile)
            for kind, condition in itertools.product(("reference", "reserve_probe", "proxy"), CONTRAST):
                with self.subTest(seed=seed, family=family, profile=profile, kind=kind, condition=condition):
                    record = run_episode(case, {"name": kind, "kind": kind}, condition, 0)
                    expected = kind == "reference" or (kind == "reserve_probe" and condition == TREATMENT)
                    self.assertEqual(record["grade"]["success"], expected)
                    replay(record, case)
                    if kind == "reserve_probe":
                        self.assertEqual(record["grade"]["wrong_repairs"], 0)
                        self.assertEqual(record["grade"]["budget_lost_at"] is None, condition == TREATMENT)

    def test_new_prompt_cannot_be_relabelled_as_a_legacy_condition(self):
        case = generate(9)
        record = run_episode(case, {"name": "r", "kind": "reference"}, TREATMENT, 0)
        for version in ("2.0.0", "2.1.0"):
            record["framework_version"] = version
            with self.assertRaisesRegex(ValueError, "unavailable"):
                replay(record, case)

    def test_explicit_long_request_budget_is_allowed_without_infinite_timeouts(self):
        config = {"name": "r", "kind": "reference", "timeout_seconds": 180}
        validate_config(config)
        for value in (0, -1, True, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                validate_config({**config, "timeout_seconds": value})


class StudyContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "study"
        self.plan = example_plan()

    def test_strict_plan_rejects_unplanned_choices_and_invalid_numbers(self):
        alterations = [{"extra_factor": "memory"}, {"schema_version": True}, {"independent_seeds": True},
                       {"minimum_useful_effect": float("nan")}, {"replicates": 0},
                       {"stopping_rule": "until_significant"}, {"failure_policy": "drop_errors"},
                       {"precision": {"confidence": .95, "half_width": .2}},
                       {"precision": {"confidence": .95, "half_width": 1e-200}},
                       {"task_distribution": {"families": ["diagnosis", "diagnosis"],
                                              "profiles": ["standard"], "domains": ["incident"]}}]
        for changes in alterations:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_plan({**self.plan, **changes})

    def test_confirmatory_gate_counts_seeds_not_repeated_calls(self):
        self.assertEqual(required_seeds(.95, .1, 2), 877)
        plan = {**self.plan, "purpose": "confirmatory", "replicates": 10000}
        with self.assertRaisesRegex(ValueError, "independent seeds"):
            prepare_study(plan, self.out)
        self.assertFalse(self.out.exists())
        plan["independent_seeds"] = required_seeds(.95, .1, 1)
        validate_plan(plan)

    def test_prepare_freezes_plan_without_model_calls(self):
        with patch("pomdp_bench.studies.secrets.randbits", side_effect=[701, 702]), \
             patch("pomdp_bench.evaluation.make_agent", side_effect=AssertionError("No model calls")):
            manifest = prepare_study(self.plan, self.out)
        self.assertEqual(manifest["study"], bind_plan(self.plan))
        self.assertEqual({c["seed"] for c in manifest["cases"]}, {701, 702})
        self.assertEqual(manifest["conditions"], list(CONTRAST))

    def test_complete_distribution_is_required_before_directory_creation(self):
        plan = copy.deepcopy(self.plan)
        plan["task_distribution"]["families"] = list(FAMILIES)
        with self.assertRaisesRegex(ValueError, "distribution changed"):
            prepare_suite(suite([0, 1], families=["diagnosis"]), plan["agents"], list(CONTRAST), 1,
                          self.out, plan["wall_seconds"], study=bind_plan(plan))
        self.assertFalse(self.out.exists())

    def test_changed_hypothesis_or_precision_is_rejected_even_if_outer_hash_is_rewritten(self):
        prepare_study(self.plan, self.out)
        path = self.out / "private" / "manifest.json"
        manifest = read_json(path)
        manifest["study"]["plan"]["minimum_useful_effect"] = .3
        write_json(path, manifest)
        write_json(self.out / "private" / "manifest.sha256.json", {"sha256": digest(manifest)})
        with self.assertRaisesRegex(ValueError, "fingerprint changed"):
            resume_suite(self.out)

    def test_schedule_pairs_arms_and_counterbalances_each_agent_over_seeds(self):
        plan = copy.deepcopy(self.plan)
        plan["independent_seeds"] = 4
        plan["agents"].append({"name": "probe", "kind": "reserve_probe"})
        with patch("pomdp_bench.studies.secrets.randbits", side_effect=[20, 21, 22, 23]):
            manifest = prepare_study(plan, self.out)
        entries = schedule(manifest)
        first = {a["name"]: Counter() for a in plan["agents"]}
        for index in range(0, len(entries), 2):
            a, b = entries[index:index+2]
            self.assertEqual((a["case_id"], a["agent"], a["replicate"]), (b["case_id"], b["agent"], b["replicate"]))
            self.assertEqual({a["condition"], b["condition"]}, set(CONTRAST))
            first[a["agent"]][a["condition"]] += 1
        for counts in first.values():
            self.assertEqual(counts[CONTROL], counts[TREATMENT])

    def test_collector_reuses_validation_resume_and_only_planned_primary_contrasts(self):
        self.plan["agents"].append({"name": "probe", "kind": "reserve_probe"})
        prepare_study(self.plan, self.out)
        report = resume_suite(self.out)
        self.assertEqual(report["paired_comparisons"], [])
        self.assertEqual(len(report["study_analysis"]["primary_comparisons"]), 2)
        _, records = validate_run(self.out)
        self.assertEqual(len(records), 8)
        with patch("pomdp_bench.evaluation.make_agent", side_effect=AssertionError("No retries")):
            self.assertEqual(resume_suite(self.out), report)

    def test_cli_prepare_collect_and_rebuild_study_analysis(self):
        path = Path(self.temp.name) / "plan.json"
        write_json(path, self.plan)
        self.assertEqual(main(["prepare-study", "--plan", str(path), "--out", str(self.out)]), 0)
        self.assertEqual(main(["resume", str(self.out)]), 0)
        before = read_json(self.out / "summary.json")["study_analysis"]
        self.assertEqual(main(["summarize", str(self.out)]), 0)
        self.assertEqual(before, read_json(self.out / "summary.json")["study_analysis"])


class StudyAnalysisTests(unittest.TestCase):
    def test_perfect_pilot_does_not_imply_zero_uncertainty_or_confirmation(self):
        manifest, records = analytical_fixture(example_plan())
        result = analyze_study(manifest, records)
        row = result["primary_comparisons"][0]
        self.assertEqual(row["observed_success_difference"], 0)
        self.assertEqual(row["simultaneous_hoeffding_interval"], [-1, 1])
        self.assertEqual(row["decision"], "exploratory_only")
        self.assertEqual(row["pilot_gate"], "no_observed_baseline_headroom")
        self.assertFalse(result["declared_precision_met"])

    def test_censored_failure_stays_in_denominator_and_yields_identification_bounds(self):
        manifest, records = analytical_fixture(example_plan())
        # Seed 0: observed treatment win. Seed 1: treatment censored, control win.
        c0 = digest(manifest["cases"][0])
        for row in records:
            if row["case_id"] == c0 and row["condition"] == CONTROL:
                row["grade"]["success"] = False
            if row["case_id"] != c0 and row["condition"] == TREATMENT:
                row["grade"].update(success=False, termination="adapter_error")
        result = analyze_study(manifest, records)["primary_comparisons"][0]
        self.assertEqual(result["pairs"], 2)
        self.assertEqual(result["observed_success_difference"], 0)
        self.assertEqual(result["censoring_identification_bounds"], [0, .5])
        self.assertEqual(result["condition_counts"][TREATMENT]["episodes"], 2)
        self.assertEqual(result["condition_counts"][TREATMENT]["censored"], 1)
        self.assertEqual(result["pilot_gate"], "resolve_execution_censoring")

    def test_both_arms_censored_cannot_identify_direction(self):
        manifest, records = analytical_fixture(example_plan())
        for row in records:
            row["grade"].update(success=False, termination="collection_interrupted")
        result = analyze_study(manifest, records)["primary_comparisons"][0]
        self.assertEqual(result["observed_success_difference"], 0)
        self.assertEqual(result["censoring_identification_bounds"], [-1, 1])

    def test_repeats_and_skins_cannot_shrink_independent_seed_uncertainty(self):
        plan = example_plan()
        a = analyze_study(*analytical_fixture(plan))
        plan["replicates"] = 3
        plan["task_distribution"]["domains"].append("data_pipeline")
        b = analyze_study(*analytical_fixture(plan))
        self.assertEqual(a["interval_half_width_before_clipping"], b["interval_half_width_before_clipping"])
        self.assertEqual(b["primary_comparisons"][0]["seed_clusters"], 2)
        self.assertEqual(b["primary_comparisons"][0]["pairs"], 12)

    def test_more_primary_agents_increase_the_simultaneous_interval(self):
        plan = example_plan()
        a = analyze_study(*analytical_fixture(plan))
        plan["agents"].append({"name": "second", "kind": "reference"})
        b = analyze_study(*analytical_fixture(plan))
        self.assertGreater(b["interval_half_width_before_clipping"], a["interval_half_width_before_clipping"])

    def test_no_intersection_only_or_duplicate_analysis(self):
        manifest, records = analytical_fixture(example_plan())
        for broken in (records[:-1], records + [records[0]]):
            with self.assertRaisesRegex(ValueError, "complete paired matrix"):
                analyze_study(manifest, broken)


if __name__ == "__main__":
    unittest.main()
