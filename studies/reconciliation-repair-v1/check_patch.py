"""Post-hoc artifact check, NOT a resumed model attempt or model success.

Replay the interrupted model's actual prefix without modifying its SQL. A
disclosed scripted suffix only submits/drains probes, refreshes and verifies.
"""
import argparse
import json
from pathlib import Path

from pomdp_bench.collection import source_hashes
from pomdp_bench.evaluation import episode_record, replay_environment
from pomdp_bench.generator import digest
from pomdp_bench.reconciliation import ReconciliationEnvironment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    if data["source_sha256"] != source_hashes():
        raise ValueError("Use frozen runtime source")
    original = next(r for r in data["records"] if r["profile"] == "capture_snapshots")
    case = next(c for c in data["cases"] if digest(c) == original["case_id"])
    env = ReconciliationEnvironment(case)
    try:
        for event in original["events"]:
            if env.step(event["action"]) != event["observation"]:
                raise ValueError("Original prefix changed")
        while not env.done:
            seen = [e["action"] for e in env.history]
            last = env.history[-1]
            if sum(a.get("command") == "workload" for a in seen) < 2:
                action = {"command": "workload", "target": 1}
            elif last["action"]["command"] == "verify":
                action = {"command": "finish"}
            elif last["action"]["command"] == "refresh":
                action = {"command": "verify"}
            elif last["action"] == {"command": "inspect", "target": "metrics"}:
                action = {"command": "wait" if last["observation"]["result"]["pending_receipts"] else "refresh"}
            else:
                action = {"command": "inspect", "target": "metrics"}
            env.step(action)
        record = episode_record(env, {"name": "post-hoc-sol-patch-with-scripted-completion", "kind": "actions", "actions": [e["action"] for e in env.history]}, 0)
    finally:
        env.close()
    replay_environment(record, case, execute_checks=True)
    result = {"purpose": "Post-hoc artifact qualification of existing model SQL on new workload, with a scripted suffix. Not another model attempt or model success.",
              "git_revision": data["git_revision"], "source_sha256": source_hashes(), "case": case,
              "original_record_sha256": digest(original), "original_model_steps": len(original["events"]),
              "scripted_suffix": record["agent"]["actions"][len(original["events"]):], "record": record}
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print({"original_model_accepted": original["grade"]["success"], "separate_artifact_accepted": record["grade"]["success"], "scripted_steps": len(result["scripted_suffix"])})


if __name__ == "__main__":
    main()
