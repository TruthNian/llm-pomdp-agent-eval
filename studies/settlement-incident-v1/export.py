"""Export complete records and independently reconstructed final business state."""
import argparse
from pathlib import Path

from pomdp_bench.collection import read_run, source_hashes
from pomdp_bench.generator import digest
from pomdp_bench.incident_runtime import Runtime
from pomdp_bench.storage import read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    manifest, records = read_run(args.run)
    if source_hashes() != manifest["source_sha256"]:
        raise ValueError("Use the collection source for fresh reconstruction")
    cases = {digest(case): case for case in manifest["cases"]}
    final_states, errors = [], []
    for record in records:
        runtime = Runtime(cases[record["case_id"]])
        try:
            for call in record["service_evidence"]["calls"]:
                if runtime.call(call["action"]) != call["response"]:
                    raise ValueError("Fresh service action disagreed with the original record")
            tables = {table: runtime.rows(f"SELECT * FROM {table} ORDER BY 1") for table in
                      ("orders", "outbox", "ledger", "logs", "config", "applied_config")}
            if record["service_evidence"]["calls"] and digest(tables) != record["service_evidence"]["calls"][-1]["response"]["state_sha256"]:
                raise ValueError("Final database differs from the original state fingerprint")
            final_states.append({"agent": record["agent"]["name"], "kind": "fresh reconstruction matching original state digest", "tables": tables})
        except (RuntimeError, ValueError) as exc:
            errors.append({"agent": record["agent"]["name"], "error": str(exc)})
        finally:
            runtime.close()
    settings = args.run / "private/settings-check.json"
    evidence = {"purpose": "Complete open incident trajectories; one constructed development scenario",
                "git_revision": manifest["git_revision"], "working_tree_dirty": manifest["working_tree_dirty"],
                "source_sha256": manifest["source_sha256"], "suite_sha256": manifest["suite_sha256"],
                "cases": manifest["cases"], "expected": manifest["expected_episodes"], "retained": len(records),
                "settings_check": read_json(settings) if settings.exists() else None,
                "records": records, "fresh_recheck_errors": errors, "fresh_final_states": final_states}
    write_json(args.out, evidence, replace=False)
    print({"retained": len(records), "accepted": sum(r["grade"]["success"] for r in records), "fresh_disagreements": len(errors)})
    if errors:
        raise SystemExit("Fresh execution disagreement retained")


if __name__ == "__main__":
    main()
