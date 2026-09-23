"""Export, freshly reconstruct, and verify the complete preregistered evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from controls import definitions
from render import render
from pomdp_bench.collection import read_run, source_hashes
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.reconciliation_runtime import Runtime
from pomdp_bench.storage import read_json

ROOT = Path(__file__).resolve().parent


def export(directory, output):
    manifest, records = read_run(directory)
    if source_hashes() != manifest["source_sha256"]:
        raise ValueError("Fresh reconstruction requires the frozen collection source")
    cases = {digest(c): c for c in manifest["cases"]}
    states, errors = [], []
    for record in records:
        runtime = Runtime(cases[record["case_id"]])
        try:
            for call in record["service_evidence"]["calls"]:
                if runtime.call(call["action"]) != call["response"]:
                    raise ValueError("Fresh execution disagrees with original response")
            states.append({"agent": record["agent"]["name"], "case_id": record["case_id"], "kind": "fresh reexecution matched" if record["events"] else "initial reconstruction only; original runtime never created", "tables": runtime.tables()})
        except (ValueError, RuntimeError) as exc:
            errors.append({"case_id": record["case_id"], "error": str(exc)})
        finally:
            runtime.close()
    data = {"purpose": "Complete preregistered strong-route ceiling screen on two constructed SQL repair contracts",
            "git_revision": manifest["git_revision"], "working_tree_dirty": manifest["working_tree_dirty"],
            "source_sha256": manifest["source_sha256"], "suite_sha256": manifest["suite_sha256"],
            "cases": manifest["cases"], "expected": manifest["expected_episodes"], "retained": len(records),
            "settings_check": read_json(directory / "private/settings-check.json"), "records": records,
            "fresh_recheck_errors": errors, "fresh_final_states": states}
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    if errors:
        raise SystemExit("Fresh execution disagreements retained")
    print({"retained": len(records), "accepted": sum(r["grade"]["success"] for r in records), "fresh_disagreements": len(errors)})


def verify():
    execution, plan = read_json(ROOT / "execution.json"), read_json(ROOT / "plan.json")
    sources = []
    for name, expected in execution["file_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Published bytes changed: "+name)
    for filename in ("control-evidence.json", "model-evidence.json"):
        data = read_json(ROOT / filename)
        model = filename.startswith("model")
        count = plan["expected_episodes"] if model else len(definitions())
        if (data["expected"] != count or data["retained"] != count or len(data["records"]) != count
                or data["working_tree_dirty"] or data["git_revision"] != execution["source_commit"] or data["fresh_recheck_errors"]):
            raise ValueError("Incomplete or mismatched evidence")
        sources.append(data["source_sha256"])
        cases = {digest(c): c for c in data["cases"]}
        if digest({"generator_version": plan["generator_version"], "cases": data["cases"]}) != plan["suite_sha256"]:
            raise ValueError("Case set changed")
        observed = [(r["profile"], r["agent"]["name"]) for r in data["records"]]
        expected = ([(c["profile"], a["name"]) for c in data["cases"] for a in plan["agents"]] if model else
                    [(p, p+"/"+v) for p, v, _ in definitions()])
        if sorted(observed) != sorted(expected):
            raise ValueError("Duplicate/missing episode")
        for record in data["records"]:
            replay(record, cases[record["case_id"]])
            if record["framework_version"] != plan["framework_version"] or record["condition"] != "open" or record["replicate"] != 0:
                raise ValueError("Version or episode settings changed")
            if model:
                if record["agent"] not in plan["agents"]:
                    raise ValueError("Model configuration changed")
                state = next(s for s in data["fresh_final_states"] if s["agent"] == record["agent"]["name"] and s["case_id"] == record["case_id"])
                calls = record["service_evidence"]["calls"]
                if calls and digest(state["tables"]) != calls[-1]["response"]["state_sha256"]:
                    raise ValueError("Fresh final state mismatch")
            else:
                expected_success = next(s for p, v, s in definitions() if record["agent"]["name"] == p+"/"+v)
                if record["grade"]["success"] != expected_success:
                    raise ValueError("Control result differs from preregistration")
        report = "trajectories.html" if model else "controls.html"
        if (ROOT / report).read_text(encoding="utf-8") != render(data):
            raise ValueError("Report does not match evidence")
        if model:
            settings = data["settings_check"]
            if (settings["settings_and_auth_bytes_unchanged"] != execution["settings_unchanged"]
                    or settings["settings_and_auth_bytes_unchanged"] != all(f["bytes_unchanged"] for f in settings["files"])):
                raise ValueError("Configuration control changed")
            if not settings["settings_and_auth_bytes_unchanged"]:
                print("Configuration-invariance control FAILED; retained, not a controlled comparison.")
        print(f"Verified {count} complete records in {filename}; no model calls or SQL execution.")
    if sources[0] != sources[1]:
        raise ValueError("Model/control package sources differ")
    artifact = read_json(ROOT / "patch-check.json")
    original = next(r for r in read_json(ROOT / "model-evidence.json")["records"] if digest(r) == artifact["original_record_sha256"])
    record, prefix = artifact["record"], artifact["original_model_steps"]
    if (prefix != len(original["events"]) or record["events"][:prefix] != original["events"]
            or record["service_evidence"]["calls"][:prefix] != original["service_evidence"]["calls"]
            or artifact["source_sha256"] != sources[0] or artifact["git_revision"] != execution["source_commit"]):
        raise ValueError("Post-hoc artifact differs from original model prefix/source")
    suffix = [e["action"] for e in record["events"][prefix:]]
    if (suffix != artifact["scripted_suffix"] or record["agent"]["kind"] != "actions"
            or any(a["command"] not in ("workload", "wait", "inspect", "refresh", "verify", "finish") for a in suffix)):
        raise ValueError("Unexpected intervention in the scripted artifact check")
    replay(record, artifact["case"])
    print("Verified separate post-hoc patch artifact; original model failures remain unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("export", "verify"))
    parser.add_argument("run", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    if args.mode == "export":
        if args.run is None or args.output is None:
            parser.error("export requires run and output")
        export(args.run, args.output)
    else:
        verify()
