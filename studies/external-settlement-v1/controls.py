"""Public-history controls and paired mechanism ablations; no model calls."""
import argparse
import copy
import json
from pathlib import Path
import subprocess

from pomdp_bench.collection import source_hashes
from pomdp_bench.evaluation import episode_record, replay
from pomdp_bench.settlement import SettlementEnvironment, make_case, policy_action
from pomdp_bench.settlement_runtime import Runtime


def local_only(request):
    history = request["history"]
    if not history:
        return {"command": "configure", "target": {"enabled": True, "retry_identity": "stable", "event_order": "version"}}
    if len(history) == 1:
        return {"command": "workload", "target": 2}
    if len(history) < 20:
        return {"command": "wait"}
    last = history[-1]
    if last["action"]["command"] == "verify":
        return {"command": "finish"}
    if last["action"]["command"] == "query":
        rows = last["observation"]["result"]["rows"]
        if rows:
            return {"command": "adjust", "target": {"order_id": rows[0][0], "delta_cents": rows[0][1], "key": "local-fix/" + str(len(history))}}
        return {"command": "verify"}
    return {"command": "query", "target": "SELECT order_id,amount_cents-book_cents AS delta FROM books WHERE amount_cents!=book_cents ORDER BY order_id"}


def slow(request):
    return {"command": "wait"} if len(request["history"]) < 12 else policy_action(request)


def definitions():
    return [
        ("public-operator", "delayed", policy_action, True),
        ("local-books-only", "delayed", local_only, False),
        ("new-key-retry", "delayed", lambda r: policy_action(r, retry_identity="attempt"), False),
        ("arrival-order", "delayed", lambda r: policy_action(r, event_order="arrival"), False),
        ("arrival-order-no-delay", "immediate_events", lambda r: policy_action(r, event_order="arrival"), True),
        ("slow-operator", "delayed", slow, False),
        ("slow-operator-no-deadline", "no_cancel_deadline", slow, True),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    if dirty:
        raise ValueError("Commit source and control protocol before publishing control evidence")
    records, cases, final_states, errors = [], [], [], []
    for name, profile, policy, expected in definitions():
        case = make_case(profile)
        if case not in cases:
            cases.append(case)
        env = SettlementEnvironment(case)
        try:
            while not env.done:
                request = {"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}
                env.step(policy(request))
            # Fixed actions encode the resulting artifact; policy source above
            # shows its causal generation from public feedback, never audit rows.
            config = {"name": name, "kind": "actions", "actions": [e["action"] for e in env.history]}
            record = episode_record(env, config, 0)
        finally:
            env.close()
        records.append(record)
        replay(record, case)
        runtime = Runtime(case)
        try:
            for call in record["service_evidence"]["calls"]:
                if runtime.call(call["action"]) != call["response"]:
                    raise ValueError("Fresh execution disagreed")
            final_states.append({"agent": name, "tables": runtime.tables()})
        finally:
            runtime.close()
        if record["grade"]["success"] != expected:
            errors.append({"agent": name, "error": "outcome differs from preregistered control"})
        print(name, json.dumps(record["grade"]))
    data = {"purpose": "Public-history control policies, encoded as their realized action artifacts; paired delay/deadline mechanism ablations, not model difficulty",
            "git_revision": revision, "working_tree_dirty": dirty, "source_sha256": source_hashes(),
            "cases": cases, "expected": len(definitions()), "retained": len(records), "records": records,
            "fresh_recheck_errors": errors, "fresh_final_states": final_states}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if errors:
        raise SystemExit("Control outcome disagreement retained")


if __name__ == "__main__":
    main()
