"""Regrade published behavior and patches without executing candidate code."""
import hashlib
import json
from pathlib import Path

from controls import configurations
from pomdp_bench.repair import RepairEnvironment, make_case


def main():
    root = Path(__file__).resolve().parent
    raw = (root / "control-evidence.json").read_bytes()
    evidence = json.loads(raw)
    execution = json.loads((root / "execution.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != execution["evidence_file_sha256"]:
        raise ValueError("Published evidence bytes changed")
    if (evidence["git_revision"] != execution["source_commit"] or evidence["working_tree_dirty"]
            or evidence["image_id"] != execution["image_id"]):
        raise ValueError("Execution identity differs")
    configs = {c["name"]: c for c in configurations()}
    rows = evidence["outcomes"]
    if evidence["expected"] != 6 or evidence["retained"] != 6 or len(rows) != 6:
        raise ValueError("Incomplete matrix")
    if {r["control"] for r in rows} != set(configs):
        raise ValueError("Control membership changed")
    count = 0
    for row in rows:
        env = RepairEnvironment(make_case(evidence["image_id"]), recorded_calls=row["execution_evidence"])
        for action in configs[row["control"]]["actions"]:
            env.step(action)
        checks = [e["observation"]["result"] for e in env.history
                  if e["observation"]["result"]["kind"] == "check"]
        if (env.grade() != row["grade"] or env.evidence()["patch"] != row["patch"]
                or env.calls != row["execution_evidence"] or checks != row["checks"]):
            raise ValueError("Recorded behavior or patch mismatch: " + row["control"])
        if env.grade()["success"] != (row["control"] == "upstream-artifact"):
            raise ValueError("Control separation failed")
        if not row["recorded_behavior_replay_passed"] or row["fresh_execution_recheck_error"] is not None:
            raise ValueError("Original execution reported a replay/recheck discrepancy")
        count += len(env.calls)
    if count != execution["original_container_calls"]:
        raise ValueError("Execution denominator changed")
    print(f"Regraded 6 published controls and {count} recorded executions; no candidate code executed.")


if __name__ == "__main__":
    main()
