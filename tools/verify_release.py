from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

EXPECTED_MODELS = {"gpt", "glm"}
EXPECTED_CONDITIONS = {"open", "explicit", "procedural"}
EXPECTED_ROOTS = {"db_pool", "cache_poison", "clock_skew", "queue_backlog"}
EXPECTED_REPLICATES = {1, 2, 3}


def main() -> int:
    trace_paths = sorted(RESULTS.glob("*.trace.json"))
    if len(trace_paths) != 72:
        raise SystemExit(f"Expected 72 traces, found {len(trace_paths)}")

    cells: Counter[tuple[str, str, str]] = Counter()
    run_ids: set[str] = set()
    for path in trace_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = payload["metadata"]
        model = metadata["model_key"]
        condition = metadata["prompt_condition"]
        root = metadata["root_cause"]
        replicate = int(metadata["replicate"])
        run_id = metadata["run_id"]

        if model not in EXPECTED_MODELS:
            raise SystemExit(f"Unexpected model key in {path.name}: {model}")
        if condition not in EXPECTED_CONDITIONS:
            raise SystemExit(f"Unexpected condition in {path.name}: {condition}")
        if root not in EXPECTED_ROOTS:
            raise SystemExit(f"Unexpected root cause in {path.name}: {root}")
        if replicate not in EXPECTED_REPLICATES:
            raise SystemExit(f"Unexpected replicate in {path.name}: {replicate}")
        if run_id in run_ids:
            raise SystemExit(f"Duplicate run ID: {run_id}")
        run_ids.add(run_id)
        cells[(model, condition, root)] += 1

        serialized = json.dumps(payload, ensure_ascii=False)
        if re.search(r'"Authorization"\s*:', serialized, re.IGNORECASE) or re.search(
            r"Bearer\s+[A-Za-z0-9._~-]{16,}", serialized,
            re.IGNORECASE,
        ):
            raise SystemExit(f"Credential-like material found in {path.name}")

    expected_cells = {
        (model, condition, root)
        for model in EXPECTED_MODELS
        for condition in EXPECTED_CONDITIONS
        for root in EXPECTED_ROOTS
    }
    if set(cells) != expected_cells or any(count != 3 for count in cells.values()):
        raise SystemExit(f"Unbalanced factorial cells: {dict(cells)}")

    combined = json.loads((RESULTS / "combined_results.json").read_text(encoding="utf-8"))
    if combined.get("n") != 72 or len(combined.get("rows", [])) != 72:
        raise SystemExit("combined_results.json does not contain 72 rows")

    with (RESULTS / "trajectory_features.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    if len(csv_rows) != 72:
        raise SystemExit(f"Expected 72 CSV rows, found {len(csv_rows)}")

    final_paths = list(RESULTS.glob("*.final.txt"))
    if len(final_paths) != 71:
        raise SystemExit(f"Expected 71 final messages, found {len(final_paths)}")

    required = [
        ROOT / "reports" / "gpt56_glm53_pomdp_final_report.html",
        ROOT / "reports" / "report_artifact.json",
        ROOT / "LICENSE",
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing release files: {missing}")

    print("Release verification passed: 72 balanced traces, 72 derived rows, 71 final messages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
