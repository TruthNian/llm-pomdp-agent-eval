"""Exploratory solver screening, never a scored or held-out model evaluation."""
from __future__ import annotations

import argparse
import hashlib
import platform
import statistics
import time
from pathlib import Path
from unittest.mock import patch

from pomdp_bench import coverage
from pomdp_bench.generator import digest
from pomdp_bench.storage import write_json


SEEDS = tuple(range(12))
SHAPES = ((36, 3, 72), (48, 3, 96), (60, 3, 120), (48, 4, 144),
          (72, 4, 216), (96, 4, 288), (96, 4, 384))
EXPLORATORY_VERSION = "dependency-cover-exploration/0"
NODE_LIMIT = 5_000


def search(env, seed, profile, limit):
    # Search sees exactly the catalogue and missing goals revealed by probe.
    obs = env.step({"command": "probe", "target": "all"})
    started = time.perf_counter()
    try:
        plan, nodes = coverage.cover_plan(obs["catalogue"], set(obs["goals"]) - set(obs["covered"]),
                                         obs["work_remaining"], node_limit=limit)
    except RuntimeError as exc:
        if str(exc) != "Public reference search limit reached; no infeasibility claim":
            raise
        plan, nodes = None, None
        outcome = "search_limit"
    else:
        outcome = "found" if plan is not None else "no_plan"
    return {"public_seed": seed, "profile": profile, "epoch": obs["epoch"],
            "case_sha256": digest(env.case), "catalogue_sha256": digest(obs["catalogue"]),
            "missing_goals": len(set(obs["goals"]) - set(obs["covered"])),
            "work_remaining": obs["work_remaining"], "node_limit": limit,
            "outcome": outcome, "states": nodes,
            "states_lower_bound": limit + 1 if outcome == "search_limit" else nodes,
            "plan_sha256": digest(plan) if plan is not None else None,
            "elapsed_seconds": round(time.perf_counter() - started, 6)}, plan


def screen():
    released, exploratory = [], []
    for profile in coverage.SCALES:
        for seed in SEEDS:
            env = coverage.CoverageEnvironment(coverage.generate(seed, profile))
            for _ in range(2):
                row, plan = search(env, seed, profile, 1_000_000)
                released.append(row)
                if plan is None:
                    break
                env.step({"command": "build", "target": plan})
                env.step({"command": "verify"})
            env.step({"command": "finish"})
            released[-1]["episode_success"] = env.grade()["success"]
    # Temporary process-local experimental dimensions; no released scale, source
    # file or collector is changed. Initial-cover-only screening is not recovery.
    for shape in SHAPES:
        profile = "probe-" + "-".join(map(str, shape))
        with patch.object(coverage, "VERSION", EXPLORATORY_VERSION), patch.object(coverage, "SCALES", {profile: shape}):
            for seed in SEEDS:
                env = coverage.CoverageEnvironment(coverage.generate(seed, profile, recovery=False))
                row, _ = search(env, seed, profile, NODE_LIMIT)
                exploratory.append(row)
    summaries = []
    for group, rows in (("released", released), ("exploratory", exploratory)):
        for profile in dict.fromkeys(r["profile"] for r in rows):
            selected = [r for r in rows if r["profile"] == profile]
            states = [r["states"] for r in selected if r["states"] is not None]
            summaries.append({"group": group, "profile": profile, "calls": len(selected),
                              "found": sum(r["outcome"] == "found" for r in selected),
                              "search_limit": sum(r["outcome"] == "search_limit" for r in selected),
                              "no_plan": sum(r["outcome"] == "no_plan" for r in selected),
                              "min_completed_states": min(states) if states else None,
                              "median_completed_states": statistics.median(states) if states else None,
                              "max_completed_states": max(states) if states else None})
    return {"purpose": "Adaptive public development screening; not preregistered model evidence or a complexity proof",
            "released_generator": coverage.VERSION, "exploratory_generator": EXPLORATORY_VERSION,
            "seeds": list(SEEDS), "exploratory_shapes": SHAPES,
            "exploratory_recovery": False, "exploratory_node_limit": NODE_LIMIT,
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(coverage.__file__))},
            "python_version": platform.python_version(),
            "interpretation": "States measure this solver only. Search-limit means unknown, not infeasible. "
                              "Completed-only medians exclude censored calls and cannot rank the full distribution. "
                              "No rejected seed is replaced. Candidate shapes do not extend the released ladder.",
            "summaries": summaries, "released_calls": released, "exploratory_calls": exploratory}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Output exists; use a new file, never replace published evidence")
    report = screen()
    write_json(args.out, report, replace=False)
    for row in report["summaries"]:
        print(row)
