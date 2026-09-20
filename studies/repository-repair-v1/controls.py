"""A fixed six-control matrix over one real upstream defect. No model calls."""
import argparse
import copy
import json
from pathlib import Path

from pomdp_bench.collection import read_run, run_suite, source_hashes
from pomdp_bench.evaluation import replay_environment
from pomdp_bench.generator import digest
from pomdp_bench.repair import DATA, make_case, suite
from pomdp_bench.storage import write_json


def configurations():
    fixed = json.loads((DATA / "upstream-actions.json").read_text(encoding="utf-8"))
    narrow = {"command": "edit", "target": {"path": "src/packaging/requirements.py",
              "old": "            self.specifier = tmp.specifier\n",
              "new": "            self.specifier = tmp.specifier\n            self.specifier.prereleases = True\n"}}
    smoke, verify, finish = {"command": "test", "target": "reproduction"}, {"command": "verify"}, {"command": "finish"}
    dirty = {"command": "edit", "target": {"path": "src/packaging/requirements.py",
             "old": "class Requirement:\n", "new": "class Requirement:\n    # Unverified later edit\n"}}
    original = json.loads((DATA / "base.json").read_text(encoding="utf-8"))["src/packaging/requirements.py"]
    exit_zero = {"command": "edit", "target": {"path": "src/packaging/requirements.py", "old": original,
                 "new": "import os\nos._exit(0)\n"}}
    tests = {"command": "edit", "target": {"path": "tests/test_requirements.py", "old": "import pytest", "new": ""}}
    sequences = {
        "unchanged": [smoke, verify, finish],
        "example-only": [narrow, smoke, verify, finish],
        "upstream-artifact": fixed,
        "unverified-later-edit": [*fixed[:-1], dirty, finish],
        "test-tampering": [tests, verify, finish],
        "exit-zero": [exit_zero, verify, finish],
    }
    return [{"name": name, "kind": "actions", "actions": copy.deepcopy(actions)} for name, actions in sequences.items()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run_suite(suite(args.image), configurations(), ["open"], 1, args.out, wall_seconds=300)
    manifest, traces = read_run(args.out)
    rows = []
    for trace in traces:
        # Independent execution is additional validation, never a replacement score.
        recheck_error = None
        try:
            replay_environment(trace, make_case(args.image), execute_checks=True)
        except (ValueError, RuntimeError) as exc:
            recheck_error = str(exc)
        rows.append({"control": trace["agent"]["name"], "grade": trace["grade"],
                     "elapsed_seconds": trace["elapsed_seconds"], "trace_sha256": digest(trace),
                     "checks": [e["observation"]["result"] for e in trace["events"]
                                if e["observation"]["result"]["kind"] == "check"],
                     "execution_evidence": trace["repository_evidence"]["calls"],
                     "patch": trace["repository_evidence"]["patch"],
                     "recorded_behavior_replay_passed": True, "fresh_execution_recheck_error": recheck_error})
    evidence = {"purpose": "Real defect and artifact controls; no model scores or difficulty calibration",
                "framework_version": manifest["framework_version"], "expected": 6, "retained": len(rows),
                "git_revision": manifest["git_revision"], "working_tree_dirty": manifest["working_tree_dirty"],
                "source_sha256": source_hashes(), "manifest_sha256": digest(manifest),
                "image_id": args.image, "task_source": make_case(args.image)["source_task_id"],
                "upstream_provenance": json.loads((DATA / "provenance.json").read_text(encoding="utf-8")),
                "outcomes": rows}
    write_json(args.out / "evidence.json", evidence, replace=False)
    by_name = {r["control"]: r for r in rows}
    correct = (len(rows) == 6 and all(r["grade"]["success"] == (r["control"] == "upstream-artifact") for r in rows)
               and all(r["fresh_execution_recheck_error"] is None for r in rows)
               and by_name["example-only"]["checks"][0]["passed"]
               and not by_name["example-only"]["checks"][1]["passed"]
               and by_name["test-tampering"]["grade"]["invalid_actions"] == 1
               and by_name["exit-zero"]["checks"][0]["execution_status"] == "invalid_response")
    print(json.dumps({"retained": len(rows), "control_gate_passed": correct,
                      "successes": {r["control"]: r["grade"]["success"] for r in rows}}))
    if not correct:
        raise SystemExit("Control gate failed; all original results and recheck discrepancies are retained")


if __name__ == "__main__":
    main()
