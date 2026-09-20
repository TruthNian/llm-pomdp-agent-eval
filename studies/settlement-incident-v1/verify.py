"""Regrade published complete trajectories without executing services or model calls."""
import hashlib
import argparse
from pathlib import Path

from controls import configurations
from render import render
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, default=Path(__file__).resolve().parent)
    root = parser.parse_args().study
    execution = read_json(root / "execution.json")
    for name, expected in execution["file_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Published bytes changed: {name}")
    plan = read_json(root / "plan.json")
    bundles = [("model-evidence.json", plan["agents"])]
    if (root / "control-evidence.json").exists():
        bundles.insert(0, ("control-evidence.json", configurations()))
    for name, agents in bundles:
        data = read_json(root / name)
        records = data["records"]
        if (data["git_revision"] != execution["source_commit"] or data["working_tree_dirty"]
                or data["fresh_recheck_errors"] or data["expected"] != len(agents)
                or data["retained"] != len(records) or len(records) != len(agents)
                or sorted(r["agent"]["name"] for r in records) != sorted(a["name"] for a in agents)):
            raise ValueError("Missing, duplicated or incorrectly bound episode")
        cases = {digest(c): c for c in data["cases"]}
        states = {s["agent"]: s for s in data["fresh_final_states"]}
        if len(states) != len(records):
            raise ValueError("Missing fresh database reconstruction")
        for record in records:
            expected_agent = next(a for a in agents if a["name"] == record["agent"]["name"])
            if record["agent"] != expected_agent or record["condition"] != "open" or record["replicate"] != 0:
                raise ValueError("Agent or interaction conditions changed")
            replay(record, cases[record["case_id"]])
            calls = record["service_evidence"]["calls"]
            if calls and digest(states[record["agent"]["name"]]["tables"]) != calls[-1]["response"]["state_sha256"]:
                raise ValueError("Reconstructed final database changed")
        print(f"Regraded {len(records)} complete episodes in {name}; no services or model calls executed.")
        if name == "model-evidence.json":
            if data["settings_check"] != {"settings_and_auth_bytes_unchanged": True}:
                raise ValueError("Local settings changed during collection")
            if (root / "trajectories.html").read_text(encoding="utf-8") != render(data):
                raise ValueError("Readable report differs from original trajectories")


if __name__ == "__main__":
    main()
