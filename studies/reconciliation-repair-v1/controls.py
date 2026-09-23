"""Run public-contract policies, retaining every outcome and full execution."""
import argparse
import copy
import json
from pathlib import Path
import subprocess

from pomdp_bench.collection import source_hashes
from pomdp_bench.evaluation import episode_record, replay_environment
from pomdp_bench.reconciliation import ReconciliationEnvironment, make_case
from pomdp_bench.reconciliation_control import policy_action


def definitions():
    return [(profile, variant, expected) for profile in ("capture_snapshots", "posting_corrections")
            for variant, expected in [("complete", True), ("normalize_only", False), ("fixed_resolver", False),
                                      ("global_identity", False), ("no_refresh", False),
                                      ("no_epoch", profile == "posting_corrections")]] + [("posting_corrections", "positive_only", False)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Freeze implementation/control protocol before publication")
    records, cases, errors = [], [], []
    for profile, variant, expected in definitions():
        case = make_case(profile)
        if case not in cases:
            cases.append(case)
        env = ReconciliationEnvironment(case)
        try:
            while not env.done:
                env.step(policy_action({"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}, variant))
            record = episode_record(env, {"name": profile+"/"+variant, "kind": "actions", "actions": [e["action"] for e in env.history]}, 0)
        finally:
            env.close()
        records.append(record)
        replay_environment(record, case, execute_checks=True)
        if record["grade"]["success"] != expected:
            errors.append(record["agent"]["name"])
        print(record["agent"]["name"], json.dumps(record["grade"]))
    data = {"purpose": "Hand-written public-contract feasibility and component controls, not general source-repair policies or model difficulty evidence",
            "git_revision": revision, "working_tree_dirty": False, "source_sha256": source_hashes(),
            "cases": cases, "expected": len(definitions()), "retained": len(records), "records": records,
            "fresh_recheck_errors": errors}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if errors:
        raise SystemExit("Control disagreements retained")


if __name__ == "__main__":
    main()
