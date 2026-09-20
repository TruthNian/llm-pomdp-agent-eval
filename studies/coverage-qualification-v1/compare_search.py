"""Pair the optimized solver with immutable 2.5.2 code on all prior search inputs."""
import argparse
import hashlib
import json
import platform
import subprocess
import time
import types
from pathlib import Path

from pomdp_bench import coverage
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json, write_json


ROOT = Path(__file__).resolve().parents[2]
BASE = "675d452db7739aa39a6d42353470292842f9e530"


def compare():
    previous = read_json(ROOT / "studies/coverage-search-v1/evidence.json")
    source = subprocess.run(["git", "show", BASE + ":pomdp_bench/coverage.py"], cwd=ROOT,
                            capture_output=True, check=True).stdout
    if hashlib.sha256(source).hexdigest() != previous["source_sha256"]["coverage.py"]:
        raise ValueError("Baseline source differs from the published search evidence")
    old = types.ModuleType("pomdp_bench._coverage_252")
    old.__package__ = "pomdp_bench"
    exec(compile(source, "coverage-at-" + BASE, "exec"), old.__dict__)
    results = []
    for i, row in enumerate(previous["released_calls"] + previous["exploratory_calls"]):
        profile = row["profile"]
        case = (coverage._generate(row["public_seed"], profile, tuple(map(int, profile.split("-")[1:])),
                                   previous["exploratory_generator"], recovery=False)
                if profile.startswith("probe-") else coverage.generate(row["public_seed"], profile))
        if digest(case) != row["case_sha256"]:
            raise ValueError("Changed generation distribution")
        env = coverage.CoverageEnvironment(case)
        while env.epoch < row["epoch"]:
            env.step(coverage.policy_action("cover_reference", {"observation": env.observation(), "history": env.history}))
        obs = env.step({"command": "probe", "target": "all"})
        if digest(obs["catalogue"]) != row["catalogue_sha256"]:
            raise ValueError("Changed public search input")
        pair = {}
        order = [("before", old.cover_plan), ("after", coverage.cover_plan)]
        for name, solve in order[::1 if i % 2 == 0 else -1]:
            started = time.perf_counter()
            try:
                plan, states = solve(obs["catalogue"], set(obs["goals"]) - set(obs["covered"]),
                                     obs["work_remaining"], node_limit=row["node_limit"])
            except RuntimeError as exc:
                if str(exc) != "Public reference search limit reached; no infeasibility claim":
                    raise
                plan, states, outcome = None, None, "search_limit"
            else:
                outcome = "found" if plan is not None else "no_plan"
            pair[name] = {"outcome": outcome, "states": states,
                          "plan_sha256": digest(plan) if plan is not None else None,
                          "elapsed_seconds": round(time.perf_counter() - started, 6)}
            for field in ("outcome", "states", "plan_sha256"):
                if pair[name][field] != row[field]:
                    raise ValueError("Solver result, search states or tie breaking changed")
        results.append({"public_seed": row["public_seed"], "profile": profile, "epoch": row["epoch"],
                        "case_sha256": row["case_sha256"], "catalogue_sha256": row["catalogue_sha256"],
                        "node_limit": row["node_limit"], **pair})
    totals = {name: round(sum(row[name]["elapsed_seconds"] for row in results), 6) for name in ("before", "after")}
    return {"baseline_commit": BASE, "baseline_source_sha256": hashlib.sha256(source).hexdigest(),
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(coverage.__file__))},
            "prior_evidence_sha256": digest(previous), "python": platform.python_version(),
            "platform": platform.system() + "/" + platform.machine(),
            "compared_calls": len(results), "all_outcomes_states_and_plans_match": True,
            "solver_seconds": totals, "measured_total_speedup": totals["before"] / totals["after"],
            "interpretation": "One paired desktop run with alternating solver order. Same search effort and outputs; "
                              "elapsed speedup is machine-dependent, not a difficulty increase or model-compute estimate.",
            "calls": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Output exists; never overwrite evidence")
    report = compare()
    write_json(args.out, report, replace=False)
    print(json.dumps({k: v for k, v in report.items() if k != "calls"}))
