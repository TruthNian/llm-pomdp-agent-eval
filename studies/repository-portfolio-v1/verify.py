"""Regrade final portfolio records; no candidate imports or container calls."""
from pathlib import Path
import hashlib

from controls import configurations
from pomdp_bench.repair import RepairEnvironment, make_case
from pomdp_bench.storage import read_json


def main():
    root = Path(__file__).resolve().parent
    execution = read_json(root / "execution.json")
    for name, expected_hash in execution["file_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected_hash:
            raise ValueError("Published execution bytes changed")
    evidence = read_json(root / "control-evidence.json")
    if (evidence["git_revision"] != execution["source_commit"] or evidence["working_tree_dirty"]
            or evidence["image_id"] != execution["image_id"]):
        raise ValueError("Execution source identity changed")
    rows = evidence["outcomes"]
    keys = {(r["task"], r["control"]) for r in rows}
    expected = {(task, c["name"]) for task in ("werkzeug_routing", "attrs_preinit", "urllib3_read")
                for c in configurations(task)}
    if len(rows) != 12 or keys != expected:
        raise ValueError("Incomplete or duplicated portfolio matrix")
    for row in rows:
        env = RepairEnvironment(make_case(evidence["image_id"], row["task"]),
                                recorded_calls=row["execution_evidence"]["calls"])
        config = next(c for c in configurations(row["task"]) if c["name"] == row["control"])
        for action in config["actions"]:
            env.step(action)
        checks = [e["observation"]["result"] for e in env.history if e["observation"]["result"]["kind"] == "check"]
        if env.grade() != row["grade"] or env.evidence() != row["execution_evidence"] or checks != row["checks"]:
            raise ValueError("Recorded portfolio behavior changed")
        if row["fresh_recheck_error"] is not None or env.grade()["success"] != (row["control"] == "upstream-artifact"):
            raise ValueError("Portfolio separation or fresh recheck failed")
        if row["control"] == "unchanged" and any(c["passed"] for c in checks):
            raise ValueError("Reproduction does not reproduce the defect")
        if row["control"] == "partial-repair" and (not checks[0]["passed"] or checks[1]["passed"]):
            raise ValueError("Reproduction-only repair was not separated")
    print("Regraded all 12 portfolio controls; original code fails every reproduction; no candidate code executed.")
    model_path = root / "model-acceptance.json"
    if model_path.exists():
        from pomdp_bench.evaluation import replay
        from pomdp_bench.generator import digest
        data = read_json(root / "model-proposals.json")
        outcomes = read_json(model_path)
        run = read_json(root / "model-execution.json")
        if (hashlib.sha256(model_path.read_bytes()).hexdigest() != run["acceptance_file_sha256"]
                or digest(data) != run["proposal_file_digest"] or outcomes["image_id"] != run["image_id"]
                or data["preparation_git_revision"] != run["proposal_preparation_commit"]
                or run["working_tree_dirty"]):
            raise ValueError("Model execution publication binding changed")
        if outcomes["proposal_file_sha256"] != digest(data) or len(outcomes["outcomes"]) != 6:
            raise ValueError("Model submission binding changed")
        for i, row in enumerate(outcomes["outcomes"]):
            proposal = data["attempts"][i]
            if (row["index"] != i or row["proposal_sha256"] != digest(proposal)
                    or row["task"] != proposal["task"] or row["model"] != proposal["agent"]["name"]
                    or row["proposal_error"] != proposal["error"]
                    or row["acceptance_executed"] != (proposal["error"] is None)):
                raise ValueError("Model attempt identity changed")
            if row["acceptance_executed"]:
                actions = [*proposal["edits"], {"command": "verify"}, {"command": "finish"}]
                if [e["action"] for e in row["trace"]["events"]] != actions:
                    raise ValueError("Acceptance did not execute the original proposed edits")
                grade = replay(row["trace"], make_case(outcomes["image_id"], row["task"]))
                if grade["success"] != row["accepted"] or row["fresh_recheck_error"] is not None:
                    raise ValueError("Model artifact acceptance mismatch")
            elif row["accepted"] or row["trace"] is not None:
                raise ValueError("Unexecuted model proposal cannot have an acceptance result")
        if (sum(r["accepted"] for r in outcomes["outcomes"]) != run["accepted_submissions"]
                or sum(r["acceptance_executed"] for r in outcomes["outcomes"]) != run["executed_submissions"]
                or sum(len(r["trace"]["repository_evidence"]["calls"]) for r in outcomes["outcomes"]
                       if r["acceptance_executed"]) != run["original_container_calls"]):
            raise ValueError("Model execution denominator changed")
        print("Regraded frozen model artifacts; these are single proposals, not interactive episodes.")


if __name__ == "__main__":
    main()
