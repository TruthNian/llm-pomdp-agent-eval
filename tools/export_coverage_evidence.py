"""Export reviewed metadata for complete coverage runs; never provider bodies or credentials."""
import copy
import hashlib
import json
from pathlib import Path
import sys

from pomdp_bench.collection import read_run, source_hashes
from pomdp_bench.generator import digest
from pomdp_bench.model_io import request_body
from pomdp_bench.storage import read_json, write_json
from pomdp_bench.worlds import Environment


def export_run(directory):
    manifest, traces = read_run(directory)
    cases = {digest(case): case for case in manifest["cases"]}
    rows = []
    for trace in traces:
        env = Environment(cases[trace["case_id"]], trace["condition"], trace["replicate"],
                          framework_version=trace["framework_version"])
        audits = trace.get("request_audit", [])
        for index, audit in enumerate(audits):
            public = {"protocol_version": 1, "task": env.contract(), "observation": env.observation(),
                      "history": copy.deepcopy(env.history)}
            raw = json.dumps(request_body(trace["agent"], public), ensure_ascii=False, allow_nan=False).encode()
            if hashlib.sha256(raw).hexdigest() != audit["request_sha256"]:
                raise ValueError("Request fingerprint differs from reconstructed public input")
            if index < len(trace["events"]):
                env.step(trace["events"][index]["action"])
        usage = trace["usage"]
        complete = usage is not None and usage["requests"] == usage["requests_with_usage"]
        rows.append({"case_id": trace["case_id"], "public_development_seed": cases[trace["case_id"]]["seed"],
                     "scale": trace["profile"], "condition": trace["condition"],
                     "agent": trace["agent"], "grade": trace["grade"],
                     "elapsed_seconds": trace["elapsed_seconds"], "sanitized_error": trace["error"],
                     "trace_sha256": digest(trace), "request_audit": audits,
                     "usage_complete": complete, "reported_usage": usage,
                     "total_input_tokens": usage["input_tokens"] if complete else None,
                     "total_output_tokens": usage["output_tokens"] if complete else None})
    return {"framework_version": manifest["framework_version"], "generator_version": manifest["generator_version"],
            "run_git_revision": manifest["git_revision"], "working_tree_dirty_at_prepare": manifest["working_tree_dirty"],
            "source_sha256": manifest["source_sha256"], "source_matches_export_checkout": manifest["source_sha256"] == source_hashes(),
            "expected_episodes": manifest["expected_episodes"], "retained_episodes": len(rows),
            "manifest_sha256": digest(manifest), "suite_sha256": manifest["suite_sha256"], "outcomes": rows}


def main():
    source, output = map(Path, sys.argv[1:])
    evidence = export_run(source)
    binding = source / "private/plan-binding.json"
    if binding.exists():
        evidence["plan_binding"] = read_json(binding)
    settings = source / "private/settings-check.json"
    if settings.exists():
        evidence["launcher_check"] = read_json(settings)
    if output.exists():
        raise ValueError("Evidence already exists; do not replace a published outcome")
    write_json(output, evidence, replace=False)
    print(json.dumps({"exported_episodes": evidence["retained_episodes"], "output": str(output)}))


if __name__ == "__main__":
    main()
