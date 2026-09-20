"""Reproduce 48 registered control episodes through the existing collector."""
import json
from pathlib import Path
import sys

from pomdp_bench.collection import run_suite
from pomdp_bench.coverage import DEPTH_SCALES, suite
from pomdp_bench.storage import write_json
from tools.export_coverage_evidence import export_run


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise ValueError("Use an unused control output directory")
    data = suite(list(range(12)), list(DEPTH_SCALES), experimental=True)
    runs = []
    for policy, condition in (("cover_reference", "open"), ("cover_solver", "solver_assisted")):
        target = output / condition
        run_suite(data, [{"name": policy, "kind": policy}], [condition], 1, target)
        runs.append(export_run(target))
    evidence = {"purpose": "Registered controls, not model scores; same qualified public graph streams",
                "expected_episodes": 48, "runs": runs}
    write_json(output / "evidence.json", evidence, replace=False)
    # Persist all observed evidence before enforcing this positive-control gate.
    successes = sum(row["grade"]["success"] for run in runs for row in run["outcomes"])
    print(json.dumps({"retained": sum(run["retained_episodes"] for run in runs), "successes": successes}))
    if successes != 48:
        raise ValueError("Registered positive-control gate failed; retain all evidence")


if __name__ == "__main__":
    main()
