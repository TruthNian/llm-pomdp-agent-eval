from __future__ import annotations

import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pomdp_bench.discovery import BUDGET, MAX_STEPS, DiscoveryEnvironment
from pomdp_bench.discovery_controls import (
    POLICIES, accepted_from_public_history, control_action, fixtures, main, make_report,
    public_request, replay_control, run_control, validate_report,
)


def fixture(visible=False, changing=True, handles=None):
    return {"handles": handles or ["private-initial", "private-replacement"],
            "visible": visible, "changing": changing}


def assemble(env):
    observed = env.step({"command": "probe"})
    env.step({"command": "prepare", "target": observed["dependency"]})
    env.step({"command": "assemble"})


class DiscoveryTransitionTests(unittest.TestCase):
    def test_observation_equivalence_until_dependency_is_revealed(self):
        a = DiscoveryEnvironment(fixture(handles=["first-a", "future-a"]))
        b = DiscoveryEnvironment(fixture(handles=["first-b", "future-b"]))
        self.assertEqual(public_request(a), public_request(b))
        # Even correctly guessing an undisclosed current/future handle grants no action.
        for target in ("first-a", "first-b", "future-a", "future-b", "unrelated"):
            self.assertEqual(a.step({"command": "prepare", "target": target}),
                             b.step({"command": "prepare", "target": target}))
        self.assertEqual(a.spent, 0)
        self.assertEqual(a.observation()["revision"], 0)
        self.assertNotEqual(a.step({"command": "probe"})["dependency"],
                            b.step({"command": "probe"})["dependency"])

    def test_future_identity_cannot_affect_prefix_even_at_change_event(self):
        a = DiscoveryEnvironment(fixture(handles=["shared", "future-a"]))
        b = DiscoveryEnvironment(fixture(handles=["shared", "future-b"]))
        actions = [{"command": "probe"}, {"command": "prepare", "target": "shared"},
                   {"command": "assemble"}, {"command": "verify"}, {"command": "status"}]
        for action in actions:
            self.assertEqual(public_request(a), public_request(b))
            self.assertEqual(a.step(action), b.step(action))
        self.assertTrue(a.observation()["dependency_stale"])
        self.assertNotIn("future-a", json.dumps(public_request(a)))
        self.assertNotEqual(a.step({"command": "probe"}), b.step({"command": "probe"}))

    def test_replacement_invalidates_pass_and_requires_new_work(self):
        env = DiscoveryEnvironment(fixture())
        assemble(env)
        observation = env.step({"command": "verify"})
        self.assertTrue(observation["result"]["passed"])
        self.assertEqual(observation["result"]["checked_revision"], 2)
        self.assertEqual(observation["revision"], 3)
        self.assertFalse(env.grade()["verified_current_state"])
        self.assertEqual(observation["assembly"], "private-initial")
        spent = env.spent
        self.assertEqual(env.step({"command": "prepare", "target": "private-initial"})["result"]["kind"],
                         "stale_dependency")
        self.assertEqual(env.step({"command": "prepare", "target": "private-replacement"})["result"]["kind"],
                         "invalid")
        self.assertEqual(env.spent, spent)
        env.step({"command": "probe"})
        self.assertEqual(env.step({"command": "assemble"})["result"]["kind"], "unresolved_dependency")
        env.step({"command": "prepare", "target": env.observation()["dependency"]})
        env.step({"command": "assemble"})
        self.assertTrue(env.step({"command": "verify"})["result"]["passed"])
        self.assertFalse(env.grade()["success"])
        env.step({"command": "finish"})
        self.assertTrue(env.grade()["success"])
        self.assertTrue(env.grade()["recovered_after_change"])
        self.assertEqual(env.grade()["external_changes"], 1)
        self.assertEqual(env.spent, BUDGET)

    def test_finish_after_old_pass_fails_both_acceptance_checks(self):
        env = DiscoveryEnvironment(fixture())
        assemble(env)
        env.step({"command": "verify"})
        env.step({"command": "finish"})
        self.assertFalse(env.grade()["success"])
        self.assertFalse(accepted_from_public_history(env.contract(), env.history))
        with self.assertRaises(RuntimeError):
            env.step({"command": "probe"})

    def test_repeated_mutation_requires_fresh_verification(self):
        for command in ("prepare", "assemble"):
            env = DiscoveryEnvironment(fixture(changing=False))
            assemble(env)
            env.step({"command": "verify"})
            action = {"command": command}
            if command == "prepare":
                action["target"] = env.observation()["dependency"]
            env.step(action)
            self.assertFalse(env.grade()["verified_current_state"])
            env.step({"command": "finish"})
            self.assertFalse(env.grade()["success"])
            self.assertFalse(accepted_from_public_history(env.contract(), env.history))

    def test_invalid_actions_are_inert_but_consume_steps(self):
        env = DiscoveryEnvironment(fixture())
        bad = [None, [], {}, {"command": []}, {"command": "probe", "target": "extra"},
               {"command": "prepare", "target": []}, {"command": "status", "fixture": "leak"}]
        for action in bad:
            self.assertEqual(env.step(action)["result"], {"kind": "invalid"})
        self.assertEqual(env.spent, 0)
        self.assertEqual(env.revision, 0)
        self.assertEqual(env.observation()["steps_remaining"], MAX_STEPS - len(bad))

    def test_probe_and_unaffordable_action_do_not_invalidate_pass(self):
        env = DiscoveryEnvironment(fixture(changing=False))
        assemble(env)
        env.step({"command": "verify"})
        for _ in range(BUDGET - env.spent):
            env.step({"command": "probe"})
        self.assertEqual(env.step({"command": "assemble"})["result"]["kind"], "budget_blocked")
        env.step({"command": "finish"})
        self.assertTrue(env.grade()["success"])
        self.assertEqual(env.grade()["redundant_probes"], 6)

    def test_finish_can_use_final_step_but_free_actions_cannot_extend_horizon(self):
        for final in ("finish", "status"):
            env = DiscoveryEnvironment(fixture(changing=False))
            assemble(env)
            env.step({"command": "verify"})
            while len(env.history) < MAX_STEPS - 1:
                env.step({"command": "status"})
            env.step({"command": final})
            self.assertEqual(env.grade()["success"], final == "finish")
            self.assertEqual(env.observation()["steps_remaining"], 0)
            self.assertEqual(env.grade()["success"], accepted_from_public_history(env.contract(), env.history))

    def test_fixture_validation_rejects_ambiguous_worlds(self):
        for bad in ({}, fixture(handles=["same", "same"]), fixture(handles=["", "ok"]),
                    fixture(visible=1), fixture(changing="yes"), {**fixture(), "seed": 1}):
            with self.assertRaises(ValueError):
                DiscoveryEnvironment(bad)

    def test_public_values_and_private_fixture_are_defensive_copies(self):
        original = fixture(visible=True)
        env = DiscoveryEnvironment(original)
        original["handles"][0] = "changed-outside"
        request = public_request(env)
        request["task"]["costs"]["probe"] = 0
        request["observation"]["result"]["kind"] = "spoofed"
        self.assertEqual(env.current, "private-initial")
        self.assertEqual(env.contract()["costs"]["probe"], 1)
        self.assertEqual(env.observation()["result"]["kind"], "start")


class DiscoveryControlTests(unittest.TestCase):
    def test_complete_factorial_controls_and_constructive_budget(self):
        report = make_report()
        validate_report(report)
        self.assertEqual(len(report["traces"]), 60)
        for f in fixtures():
            for policy in POLICIES:
                trace = run_control(f, policy)
                expected = policy == "adaptive" or (not f["changing"] and
                            (policy == "never_revise" or policy == "static" and f["visible"]))
                self.assertEqual(trace["grade"]["success"], expected, (f, policy))
                self.assertEqual(replay_control(trace), trace["grade"])
                if policy == "adaptive":
                    self.assertEqual(trace["grade"]["cost"], 6 + 6 * f["changing"] - f["visible"])
                    self.assertEqual(trace["grade"]["probes"], 1 + f["changing"] - f["visible"])
                    self.assertEqual(trace["grade"]["steps"], 5 + 4 * f["changing"] - f["visible"])
                    self.assertEqual(trace["grade"]["redundant_probes"], 0)

    def test_controls_are_invariant_to_handle_relabeling(self):
        for visible in (False, True):
            for changing in (False, True):
                for policy in POLICIES:
                    a = run_control(fixture(visible, changing), policy)
                    b = run_control(fixture(visible, changing, ["新依赖", "替代依赖"]), policy)
                    self.assertEqual(a["grade"], b["grade"])

    def test_policy_input_has_only_public_keys_even_after_replacement(self):
        env = DiscoveryEnvironment(fixture())
        while not env.done:
            request = json.loads(json.dumps(public_request(env)))
            self.assertEqual(set(request), {"task", "observation", "history"})
            if env.dependency != "private-replacement":
                self.assertNotIn("private-replacement", json.dumps(request))
            env.step(control_action("adaptive", request))
        self.assertTrue(env.grade()["success"])

    def test_acceptance_agrees_on_perturbed_trajectories(self):
        # Follow the successful witness with occasional mutations, invalid actions,
        # premature handover and wasted probes. The second oracle reads public history.
        rng = random.Random(7)
        for index in range(250):
            env = DiscoveryEnvironment(fixture(bool(index % 2), bool(index % 3)))
            while not env.done:
                action = control_action("adaptive", public_request(env))
                if rng.random() < 0.3:
                    action = rng.choice([{"command": c} for c in ("finish", "probe", "assemble", "verify", "status")]
                                        + [{"command": "prepare", "target": "unknown"}])
                env.step(action)
            self.assertEqual(env.grade()["success"], accepted_from_public_history(env.contract(), env.history),
                             env.history)

    def test_replay_rejects_trace_changes_and_post_terminal_actions(self):
        original = run_control(fixture(), "adaptive")
        for field in ("action", "observation", "grade", "grade_type", "contract", "version", "policy",
                      "truncated", "post_terminal"):
            trace = copy.deepcopy(original)
            if field == "action":
                trace["events"][0]["action"] = {"command": "status"}
            elif field == "observation":
                trace["events"][0]["observation"]["remaining"] += 1
            elif field == "grade":
                trace["grade"]["success"] = False
            elif field == "grade_type":
                trace["grade"]["success"] = 1
            elif field == "contract":
                trace["contract"]["budget"] += 1
            elif field == "version":
                trace["version"] = "dependency-recovery/0"
            elif field == "policy":
                trace["policy"] = "never_revise"
            elif field == "truncated":
                trace["events"].pop()
            else:
                trace["events"].append(copy.deepcopy(trace["events"][-1]))
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay_control(trace)

    def test_report_rejects_missing_duplicate_extra_and_altered_evidence(self):
        original = make_report()
        for change in ("missing", "duplicate", "unplanned", "summary", "source"):
            report = copy.deepcopy(original)
            if change == "missing":
                report["traces"].pop()
            elif change == "duplicate":
                report["traces"].append(copy.deepcopy(report["traces"][0]))
            elif change == "unplanned":
                report["traces"][0] = run_control(fixture(), "adaptive")
            elif change == "summary":
                report["summary"][0]["policies"]["adaptive"]["successes"] = 0
            else:
                report["source_sha256"]["discovery.py"] = "0" * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_report(report)

    def test_cli_writes_replays_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "controls.json"
            self.assertEqual(main(["--out", str(path)]), 0)
            self.assertEqual(main(["--validate", str(path)]), 0)
            original = path.read_bytes()
            with self.assertRaises(SystemExit):
                main(["--out", str(path)])
            # Simulate another writer arriving after the initial existence check.
            with patch.object(Path, "exists", return_value=False), self.assertRaises(SystemExit):
                main(["--out", str(path)])
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
