"""Independently execute frozen model-proposed artifacts, without another model call."""
import argparse
from pathlib import Path

from proposals import proposal_edits
from pomdp_bench.collection import read_run, run_suite
from pomdp_bench.evaluation import replay_environment
from pomdp_bench.generator import digest
from pomdp_bench.repair import make_case, suite
from pomdp_bench.storage import read_json, write_json

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = read_json(HERE / "model-proposals.json")
    plan = read_json(HERE / "proposal_plan.json")
    if data["plan_sha256"] != digest(plan) or len(data["attempts"]) != plan["expected_attempts"]:
        raise ValueError("Proposal plan or matrix changed")
    args.out.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for index, row in enumerate(data["attempts"]):
        task, model = plan["order"][index]
        if row["index"] != index or row["task"] != task or row["agent"]["name"] != model:
            raise ValueError("Submission identity changed")
        result = {"index": index, "task": task, "model": model, "proposal_sha256": digest(row),
                  "acceptance_executed": False, "accepted": False, "proposal_error": row["error"],
                  "trace": None, "fresh_recheck_error": None}
        if row["error"] is None:
            edits, patch = proposal_edits(plan, task, row["action"])
            if edits != row["edits"] or patch != row["patch"]:
                raise ValueError("Proposed source patch changed")
            actions = [*edits, {"command": "verify"}, {"command": "finish"}]
            output = args.out / str(index)
            run_suite(suite(args.image, [task]),
                      [{"name": model + "/single-proposal-artifact", "kind": "actions", "actions": actions}],
                      ["open"], 1, output, wall_seconds=300)
            _, traces = read_run(output)
            trace = traces[0]
            result.update(acceptance_executed=True, accepted=trace["grade"]["success"], trace=trace)
            try:
                replay_environment(trace, make_case(args.image, task), execute_checks=True)
            except (ValueError, RuntimeError) as exc:
                result["fresh_recheck_error"] = str(exc)
        outcomes.append(result)
    write_json(args.out / "evidence.json", {"purpose": "Single-proposal artifact acceptance; not interactive agent completion",
               "proposal_file_sha256": digest(data), "image_id": args.image,
               "expected_submissions": 6, "retained_submissions": len(outcomes), "outcomes": outcomes}, replace=False)
    print({"retained": len(outcomes), "accepted": sum(r["accepted"] for r in outcomes),
           "executed": sum(r["acceptance_executed"] for r in outcomes)})
    if any(r["fresh_recheck_error"] is not None for r in outcomes):
        raise SystemExit("Fresh execution disagreement retained; original acceptance was not replaced")


if __name__ == "__main__":
    main()
