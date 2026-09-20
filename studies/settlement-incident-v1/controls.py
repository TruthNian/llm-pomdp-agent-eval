"""Execute complete incident trajectories; no candidate source or model calls."""
import argparse
from pathlib import Path

from pomdp_bench.collection import read_run, run_suite
from pomdp_bench.evaluation import replay_environment
from pomdp_bench.incident import make_case, suite
from pomdp_bench.storage import write_json


def configurations():
    config = {"command": "configure", "target": {"service": "worker", "patch": {"protocol": "compatible", "dedupe": "order", "batch": 16}}}
    verify, finish = {"command": "verify"}, {"command": "finish"}
    return [
        {"name": "runbook-operator", "kind": "incident_operator"},
        {"name": "healthy-process-only", "kind": "actions", "actions": [{"command": "inspect", "target": "metrics"}, finish]},
        {"name": "config-without-restart", "kind": "actions", "actions": [config, verify, finish]},
        {"name": "future-only-repair", "kind": "actions", "actions": [config, {"command": "restart", "target": "worker"}, verify, finish]},
        {"name": "blind-rollback", "kind": "actions", "actions": [{"command": "rollback", "target": "worker"}, verify, finish]},
        {"name": "overinvestigate", "kind": "actions", "actions": [{"command": "inspect", "target": "metrics"}] * 60},
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run_suite(suite(), configurations(), ["open"], 1, args.out)
    manifest, records = read_run(args.out)
    errors = []
    for row in records:
        try:
            replay_environment(row, make_case(), execute_checks=True)
        except (RuntimeError, ValueError) as exc:
            errors.append({"agent": row["agent"]["name"], "error": str(exc)})
    write_json(args.out / "evidence.json", {"purpose": "Executable incident trajectory controls; not model performance",
               "git_revision": manifest["git_revision"], "working_tree_dirty": manifest["working_tree_dirty"],
               "source_sha256": manifest["source_sha256"], "records": records, "fresh_recheck_errors": errors}, replace=False)
    if errors or any(r["grade"]["success"] != (r["agent"]["name"] == "runbook-operator") for r in records):
        raise SystemExit("Incident control separation failed; all trajectories retained")
    print("All six controls separated; every action reproduced against fresh HTTP services and database.")


if __name__ == "__main__":
    main()
