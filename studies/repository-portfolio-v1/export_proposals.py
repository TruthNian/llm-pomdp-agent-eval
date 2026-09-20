"""Export parsed public proposals after checking all request/source bindings."""
import hashlib
import json
from pathlib import Path
import sys

from proposals import proposal_edits
from pomdp_bench.collection import source_hashes
from pomdp_bench.generator import digest
from pomdp_bench.model_io import request_body
from pomdp_bench.storage import read_json, write_json


def main():
    directory, destination = Path(sys.argv[1]), Path(sys.argv[2])
    private = directory / "private"
    manifest = read_json(private / "manifest.json")
    plan = read_json(Path(__file__).with_name("proposal_plan.json"))
    if (digest(manifest) != read_json(private / "manifest-binding.json")["sha256"]
            or digest(plan) != manifest["plan_sha256"] or source_hashes() != manifest["source_sha256"]):
        raise ValueError("Manifest, plan or source drift")
    if hashlib.sha256(Path(__file__).with_name("proposals.py").read_bytes()).hexdigest() != manifest["launcher_sha256"]:
        raise ValueError("Proposal launcher changed during collection")
    agents = {a["name"]: a for a in plan["agents"]}
    records, verified = [], 0
    for index, (task, name) in enumerate(plan["order"]):
        row = read_json(private / f"attempt-{index}.json")
        if (row["index"], row["task"], row["agent"]["name"]) != (index, task, name):
            raise ValueError("Attempt identity drift")
        if row["agent"] != agents[name]:
            raise ValueError("Attempt configuration differs from the frozen plan")
        raw = json.dumps(request_body(row["agent"], manifest["public_requests"][task]),
                         ensure_ascii=False, allow_nan=False).encode()
        fingerprint = hashlib.sha256(raw).hexdigest()
        start = read_json(private / f"start-{index}.json")
        if (start["request_sha256"] != fingerprint or start["task"] != task
                or start["agent"] != name or start["plan_sha256"] != digest(plan)):
            raise ValueError("Attempt start is not bound to its public request")
        for audit in row["request_audit"]:
            if audit["request_sha256"] != fingerprint:
                raise ValueError("Actual model request differs from the frozen public context")
            verified += 1
        if row["error"] is None:
            edits, patch = proposal_edits(plan, task, row["action"])
            if edits != row["edits"] or patch != row["patch"]:
                raise ValueError("Model proposal was modified after collection")
        records.append(row)
    settings = read_json(private / "settings-check.json")
    export = {"purpose": plan["purpose"], "localization_assistance": plan["localization_assistance"],
              "framework_version": plan["framework_version"], "plan_sha256": digest(plan),
              "preparation_git_revision": manifest["git_revision"], "source_sha256": manifest["source_sha256"],
              "launcher_sha256": manifest["launcher_sha256"], "manifest_sha256": digest(manifest),
              "expected_attempts": plan["expected_attempts"], "retained_attempts": len(records),
              "request_fingerprints_verified": verified, **settings, "attempts": records}
    write_json(destination, export, replace=False)
    print(json.dumps({"retained": len(records), "requests_verified": verified,
                      "valid_proposals": sum(r["edits"] is not None for r in records), **settings}))


if __name__ == "__main__":
    main()
