"""Regrade every published outcome and verify report bytes without services."""
import hashlib
from pathlib import Path

from controls import definitions
from render import render
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json


def main():
    root = Path(__file__).resolve().parent
    execution = read_json(root / "execution.json")
    for name, expected in execution["file_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Published bytes changed: " + name)
    plan = read_json(root / "plan.json")
    for name, expected_count in (("control-evidence.json", 7), ("model-evidence.json", plan["expected_episodes"])):
        data = read_json(root / name)
        if (data["git_revision"] != execution["source_commit"] or data["working_tree_dirty"] or data["fresh_recheck_errors"]
                or data["expected"] != expected_count or data["retained"] != expected_count or len(data["records"]) != expected_count):
            raise ValueError("Incomplete or incorrectly bound evidence")
        cases = {digest(c): c for c in data["cases"]}
        states = {s["agent"]: s for s in data["fresh_final_states"]}
        names = [r["agent"]["name"] for r in data["records"]]
        expected_names = [a["name"] for a in plan["agents"]] if name.startswith("model") else [d[0] for d in definitions()]
        if sorted(names) != sorted(expected_names) or len(states) != len(names):
            raise ValueError("Missing or duplicate episode/state")
        for record in data["records"]:
            replay(record, cases[record["case_id"]])
            if record["framework_version"] != plan["framework_version"] or record["condition"] != "open" or record["replicate"] != 0:
                raise ValueError("Version or interaction settings changed")
            if name.startswith("model"):
                if record["agent"] != next(a for a in plan["agents"] if a["name"] == record["agent"]["name"]):
                    raise ValueError("Model configuration changed")
            else:
                spec = next(d for d in definitions() if d[0] == record["agent"]["name"])
                if record["profile"] != spec[1] or record["grade"]["success"] != spec[3]:
                    raise ValueError("Control qualification changed")
            calls = record["service_evidence"]["calls"]
            if calls and digest(states[record["agent"]["name"]]["tables"]) != calls[-1]["response"]["state_sha256"]:
                raise ValueError("Fresh final state hash disagrees")
        report = "trajectories.html" if name.startswith("model") else "controls.html"
        if (root / report).read_text(encoding="utf-8") != render(data):
            raise ValueError("Readable report changed")
        if name.startswith("model"):
            # Verifying that adverse evidence was preserved is not the same as
            # passing the configuration-invariance control. Never rewrite false.
            observed = data["settings_check"]
            declared = execution["configuration_invariance"]
            if observed != {"settings_and_auth_bytes_unchanged": declared["passed"]} or type(declared["passed"]) is not bool:
                raise ValueError("Configuration-invariance result changed")
            if not declared["passed"]:
                if not declared.get("limitation"):
                    raise ValueError("Failed invariance control needs an explicit limitation")
                print("Configuration-invariance control FAILED; retained and disclosed. Not a controlled model comparison.")
        print(f"Regraded {expected_count} complete records in {name}; no services or model calls.")


if __name__ == "__main__":
    main()
