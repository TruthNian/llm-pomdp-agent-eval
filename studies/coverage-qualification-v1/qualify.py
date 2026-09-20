"""Fixed, offline candidate qualification; no model calls or second collector."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import time
from pathlib import Path

from pomdp_bench import __version__, coverage
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json, write_json


ROOT = Path(__file__).resolve().parents[2]
CONTROLS = ("reference", "greedy", "rarest", "greedy_relaxed", "rarest_relaxed",
            "no_recovery", "no_recovery_stable")


def validate_plan(plan):
    if (plan["schema_version"] != 1 or plan["generator_version"] != "dependency-cover-exploration/0"
            or plan["controls"] != list(CONTROLS)
            or type(plan["node_limit_per_reference_decision"]) is not int
            or not 1 <= plan["node_limit_per_reference_decision"] <= 1_000_000
            or not plan["public_seeds"] or not plan["shapes"]
            or len(set(plan["public_seeds"])) != len(plan["public_seeds"])
            or any(type(s) is not int or s < 0 for s in plan["public_seeds"])
            or len({tuple(s) for s in plan["shapes"]}) != len(plan["shapes"])
            or len(plan["shapes"]) * len(plan["public_seeds"]) != plan["expected_cases"]
            or plan["expected_cases"] * len(CONTROLS) != plan["expected_control_rows"]):
        raise ValueError("Invalid fixed qualification matrix")
    for shape in plan["shapes"]:
        coverage._generate(0, "dimension-check", shape, plan["generator_version"])


def request(env):
    return {"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}


def check_replay(case, env):
    replayed = coverage.CoverageEnvironment(case)
    for event in env.history:
        if replayed.step(event["action"]) != event["observation"]:
            raise ValueError("Offline control observation does not replay")
    if not replayed.done:
        replayed.abort(env.reason)
    if replayed.grade() != env.grade():
        raise ValueError("Offline control grade does not replay")


def evaluate(case, control, node_limit, initial_plan=None):
    env, searches = coverage.CoverageEnvironment(case), []
    initial = None
    while not env.done:
        public = request(env)
        obs = public["observation"]
        missing = set(obs["goals"]) - set(obs["covered"])
        ready = missing and len(obs["catalogue"]) == len(obs["operations"])
        if control.startswith("no_recovery") and obs["epoch"]:
            action = {"command": "finish"}
        elif control.startswith("no_recovery") and ready:
            if initial_plan is None:
                raise ValueError("A non-revising control requires an observed initial plan")
            action = {"command": "build", "target": initial_plan}
        elif control == "reference" and ready:
            started = time.perf_counter()
            try:
                result, states = coverage.cover_plan(obs["catalogue"], missing, obs["work_remaining"],
                                                     node_limit=node_limit)
            except RuntimeError as exc:
                if str(exc) != "Public reference search limit reached; no infeasibility claim":
                    raise
                result, states, outcome = None, None, "search_limit"
            else:
                outcome = "found" if result is not None else "no_plan"
            searches.append({"epoch": obs["epoch"], "outcome": outcome, "states": states,
                             "states_lower_bound": node_limit + 1 if outcome == "search_limit" else states,
                             "node_limit": node_limit, "catalogue_sha256": digest(obs["catalogue"]),
                             "plan_sha256": digest(result) if result is not None else None,
                             "elapsed_seconds": round(time.perf_counter() - started, 6)})
            if result is None:
                env.abort("reference_" + outcome)
                break
            # Check the solution as a set union, independently of search internals.
            if (len(result) > obs["work_remaining"] or len(set(result)) != len(result)
                    or not set(result) <= set(obs["catalogue"])
                    or not set().union(*(set(obs["catalogue"][r]) for r in result)) >= missing):
                raise ValueError("Reference returned an invalid public cover")
            if not obs["epoch"]:
                initial = result[:]
            action = {"command": "build", "target": result}
        else:
            policy = ("cover_greedy" if control.startswith("greedy") else
                      "cover_rarest" if control.startswith("rarest") else "cover_reference")
            action = coverage.policy_action(policy, public)
        env.step(action)
    check_replay(case, env)
    trace = {"contract": env.contract(), "initial_observation": coverage.CoverageEnvironment(case).observation(),
             "events": env.history, "grade": env.grade()}
    return {"control": control, "case_sha256": digest(case), "grade": env.grade(),
            "trace_sha256": digest(trace), "searches": searches, "replay_verified": True,
            "initial_plan_source": "same public initial catalogue and work allowance"
                                   if control.startswith("no_recovery") else None}, initial


def qualify(plan, progress=lambda _: None):
    validate_plan(plan)
    rows = []
    for shape in plan["shapes"]:
        profile = "probe-" + "-".join(map(str, shape))
        for seed in plan["public_seeds"]:
            def case(recovery=True, slack=0):
                return coverage._generate(seed, profile, shape, plan["generator_version"],
                                          recovery=recovery, slack=slack)
            base, stable, relaxed = case(), case(False), case(slack=shape[0])
            if base["epochs"][0] != stable["epochs"][0] or base["epochs"] != relaxed["epochs"]:
                raise ValueError("Ablation changed the sampled catalogue")
            initial = None
            for control in CONTROLS:
                selected = stable if control.endswith("_stable") else relaxed if control.endswith("_relaxed") else base
                if control.startswith("no_recovery") and initial is None:
                    row = {"control": control, "case_sha256": digest(selected), "grade": None,
                           "not_executed_reason": "initial_reference_plan_unavailable",
                           "searches": [], "replay_verified": None}
                else:
                    row, found = evaluate(selected, control, plan["node_limit_per_reference_decision"], initial)
                    if control == "reference":
                        initial = found
                row.update(public_seed=seed, profile=profile)
                rows.append(row)
            progress({"profile": profile, "seed": seed,
                      "reference": rows[-len(CONTROLS)]["grade"]["termination"],
                      "searches": rows[-len(CONTROLS)]["searches"]})
    if len(rows) != plan["expected_control_rows"]:
        raise ValueError("Incomplete qualification matrix")
    summaries = []
    expected = {"reference": True, "greedy": False, "rarest": False, "greedy_relaxed": True,
                "rarest_relaxed": True, "no_recovery": False, "no_recovery_stable": True}
    for shape in plan["shapes"]:
        profile = "probe-" + "-".join(map(str, shape))
        selected = [r for r in rows if r["profile"] == profile]
        summary = {"profile": profile, "controls": {}}
        for name in CONTROLS:
            group = [r for r in selected if r["control"] == name]
            summary["controls"][name] = {
                "planned": len(group), "executed": sum(r["grade"] is not None for r in group),
                "successes": sum(bool(r["grade"] and r["grade"]["success"]) for r in group),
                "terminations": {reason: sum(r["grade"] is not None and r["grade"]["termination"] == reason for r in group)
                                 for reason in sorted({r["grade"]["termination"] for r in group if r["grade"] is not None})}}
        summary["offline_gate_passed"] = all(
            r["grade"] is not None and r["grade"]["termination"] == "finished"
            and r["grade"]["success"] == expected[r["control"]] for r in selected)
        summary["model_discrimination_established"] = False
        summaries.append(summary)
    return {"plan": plan, "plan_sha256": digest(plan), "framework_version": __version__,
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(coverage.__file__))},
            "git_revision": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                           text=True, capture_output=True).stdout.strip(),
            "working_tree_dirty": bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True,
                                                      text=True, capture_output=True).stdout.strip()),
            "interpretation": "Offline controls only. Non-revising ablations reuse the plan obtained from the "
                              "same public initial catalogue; they measure recovery necessity, not independent solver speed. "
                              "Missing prerequisites remain unexecuted, not invented failures. No scored scales are added.",
            "control_rows": rows, "summaries": summaries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_name("plan.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Output exists; never replace published evidence")
    result = qualify(read_json(args.plan), lambda row: print(json.dumps(row), flush=True))
    write_json(args.out, result, replace=False)
    print(json.dumps(result["summaries"]))
