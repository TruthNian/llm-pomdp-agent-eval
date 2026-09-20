"""Fixed matrix: three real tasks x unchanged/partial/upstream/stale controls."""
import argparse
import json
from pathlib import Path

from pomdp_bench.collection import read_run, run_suite
from pomdp_bench.evaluation import replay_environment
from pomdp_bench.generator import digest
from pomdp_bench.repair import make_case, suite
from pomdp_bench.repair_portfolio import ROOT, TASKS
from pomdp_bench.storage import write_json


def configurations(task):
    fixed = json.loads((ROOT / task / "upstream-actions.json").read_text(encoding="utf-8"))
    if task == "werkzeug_routing":
        partial = [a for a in fixed[:-2] if a["target"]["path"].endswith("/map.py")]
    elif task == "attrs_preinit":
        partial = []
        for action in fixed[:-2]:
            action = json.loads(json.dumps(action))
            # Keep correct default/required argument forwarding, omit the factory branch.
            if 'lines.append(f"if {arg_name} is not NOTHING:")' in action["target"]["new"]:
                continue
            partial.append(action)
    else:
        partial = json.loads(json.dumps(fixed[:-2]))
        # Drain old buffered data but discard newly decoded data: plausible incomplete repair.
        for action in partial:
            action["target"]["new"] = action["target"]["new"].replace("                self._decoded_buffer.put(data)\n", "")
    verify, finish = {"command": "verify"}, {"command": "finish"}
    smoke = {"command": "test", "target": "reproduction"}
    first = fixed[0]["target"]
    dirty = {"command": "edit", "target": {"path": first["path"], "old": first["new"],
                                          "new": first["new"] + "\n# Later unverified change\n"}}
    sequences = {"unchanged": [smoke, verify, finish],
                 "partial-repair": [*partial, smoke, verify, finish],
                 "upstream-artifact": fixed,
                 "unverified-later-edit": [*fixed[:-1], dirty, finish]}
    return [{"name": name, "kind": "actions", "actions": actions} for name, actions in sequences.items()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for task in TASKS:
        output = args.out / task
        run_suite(suite(args.image, [task]), configurations(task), ["open"], 1, output, wall_seconds=300)
        manifest, traces = read_run(output)
        for trace in traces:
            error = None
            try:
                replay_environment(trace, make_case(args.image, task), execute_checks=True)
            except (ValueError, RuntimeError) as exc:
                error = str(exc)
            rows.append({"task": task, "control": trace["agent"]["name"], "grade": trace["grade"],
                         "elapsed_seconds": trace["elapsed_seconds"], "trace_sha256": digest(trace),
                         "checks": [e["observation"]["result"] for e in trace["events"]
                                    if e["observation"]["result"]["kind"] == "check"],
                         "execution_evidence": trace["repository_evidence"],
                         "fresh_recheck_error": error})
    evidence = {"purpose": "Real artifact controls, not model performance or frontier difficulty",
                "framework_version": manifest["framework_version"], "expected": 12, "retained": len(rows),
                "git_revision": manifest["git_revision"], "working_tree_dirty": manifest["working_tree_dirty"],
                "image_id": args.image, "outcomes": rows}
    write_json(args.out / "evidence.json", evidence, replace=False)
    gate = len(rows) == 12
    for row in rows:
        gate &= row["grade"]["success"] == (row["control"] == "upstream-artifact")
        gate &= row["fresh_recheck_error"] is None
        if row["control"] == "partial-repair":
            gate &= len(row["checks"]) == 2 and row["checks"][0]["passed"] and not row["checks"][1]["passed"]
        if row["control"] == "unchanged":
            gate &= len(row["checks"]) == 2 and not any(c["passed"] for c in row["checks"])
    print(json.dumps({"retained": len(rows), "gate_passed": gate,
                      "results": [{"task": r["task"], "control": r["control"], "grade": r["grade"]} for r in rows]}))
    if not gate:
        raise SystemExit("Portfolio gate failed; original matrix and recheck discrepancies retained")


if __name__ == "__main__":
    main()
