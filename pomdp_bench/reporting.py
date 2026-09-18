"""Failure-inclusive summaries; paired uncertainty resamples seed clusters."""
from __future__ import annotations

import itertools
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .generator import digest


def interval(values: list[tuple[str, float]], resamples=1000) -> list[float] | None:
    grouped = defaultdict(list)
    for cluster, value in values:
        grouped[cluster].append(value)
    if len(grouped) < 2:
        return None
    # A cluster is a generator seed, including repeats and all semantic skins.
    clusters = list(grouped.values())
    rng = random.Random(20260918)
    draws = []
    for _ in range(resamples):
        sample = [x for _ in clusters for x in rng.choice(clusters)]
        draws.append(mean(sample))
    draws.sort()
    return [draws[int(resamples * 0.025)], draws[min(resamples - 1, int(resamples * 0.975))]]


def cell(rows: list[dict]) -> dict:
    successes = sum(r["grade"]["success"] for r in rows)
    cost = sum(r["grade"]["cost"] for r in rows)
    usages = [r["usage"] for r in rows]
    complete_usage = all(u is not None and u["requests"] == u["requests_with_usage"] for u in usages)
    input_tokens = sum(u["input_tokens"] for u in usages) if complete_usage else None
    output_tokens = sum(u["output_tokens"] for u in usages) if complete_usage else None
    return {"episodes": len(rows), "unique_cases": len({r["case_id"] for r in rows}),
            "seed_clusters": len({r["cluster_id"] for r in rows}), "successes": successes,
            "success_rate": successes / len(rows),
            "success_cluster_bootstrap95": interval([(r["cluster_id"], int(r["grade"]["success"])) for r in rows]),
            "adapter_failures": sum(r["grade"]["termination"] in ("adapter_error", "internal_error") for r in rows),
            "mean_action_cost": cost / len(rows), "action_cost_per_accepted_completion": cost / successes if successes else None,
            "mean_steps": mean(r["grade"]["steps"] for r in rows),
            "mean_diagnostic_cost": mean(r["grade"]["diagnostic_cost"] for r in rows),
            "mean_tests_after_certainty": mean(r["grade"]["tests_after_certainty"] for r in rows),
            "completion_budget_lost_rate": mean(r["grade"]["budget_lost_at"] is not None for r in rows),
            "wrong_repair_rate": mean(r["grade"]["wrong_repairs"] > 0 for r in rows),
            "proxy_attempt_rate": mean(r["grade"]["proxy_attempts"] > 0 for r in rows),
            "mean_elapsed_seconds": mean(r["elapsed_seconds"] for r in rows),
            "total_input_tokens": input_tokens, "total_output_tokens": output_tokens,
            "input_tokens_per_accepted_completion": input_tokens / successes if successes and input_tokens is not None else None,
            "output_tokens_per_accepted_completion": output_tokens / successes if successes and output_tokens is not None else None}


def paired(left: list[dict], right: list[dict]) -> dict:
    def keyed(rows):
        return {(r["case_id"], r["replicate"]): r for r in rows}
    a, b = keyed(left), keyed(right)
    if a.keys() != b.keys():
        return {"comparable": False, "reason": "Unmatched case/replicate sets; no intersection-only estimate"}
    diffs = [(a[k]["cluster_id"], int(a[k]["grade"]["success"]) - int(b[k]["grade"]["success"])) for k in sorted(a)]
    return {"comparable": True, "pairs": len(diffs), "left_minus_right_success_rate": mean(d for _, d in diffs),
            "cluster_bootstrap95": interval(diffs), "left_only_success": sum(d == 1 for _, d in diffs),
            "right_only_success": sum(d == -1 for _, d in diffs)}


def summarize(records: list[dict]) -> dict:
    if not records:
        raise ValueError("No records")
    seen, configs, suites = set(), {}, set()
    groups, overall = defaultdict(list), defaultdict(list)
    for row in records:
        name, condition = row["agent"]["name"], row["condition"]
        key = (name, condition, row["case_id"], row["replicate"])
        if key in seen:
            raise ValueError("Duplicate episode")
        seen.add(key)
        fingerprint = digest(row["agent"])
        if name in configs and configs[name] != fingerprint:
            raise ValueError("Same agent name refers to different configurations")
        configs[name] = fingerprint
        suites.add(row.get("suite_sha256"))
        groups[(name, condition, row["family"], row["profile"], row["domain"])].append(row)
        overall[(name, condition)].append(row)
    if len(suites) != 1:
        raise ValueError("Do not pool different suites")
    comparisons, rescue = [], []
    for condition in sorted({c for _, c in overall}):
        names = sorted(n for n, c in overall if c == condition)
        for left, right in itertools.combinations(names, 2):
            comparisons.append({"left": left, "right": right, "condition": condition,
                                **paired(overall[left, condition], overall[right, condition])})
    for name in sorted(configs):
        if (name, "open") in overall and (name, "procedural") in overall:
            rescue.append({"agent": name, "contrast": "procedural-minus-open",
                           **paired(overall[name, "procedural"], overall[name, "open"])})
    return {"schema_version": 1, "episodes": len(records),
            "overall": [{"agent": n, "condition": c, **cell(rows)} for (n, c), rows in sorted(overall.items())],
            "strata": [{"agent": k[0], "condition": k[1], "family": k[2], "profile": k[3], "domain": k[4],
                        **cell(rows)} for k, rows in sorted(groups.items())],
            "paired_comparisons": comparisons, "prompt_rescue": rescue,
            "interpretation": [
                "Bootstrap intervals resample generator seeds; repeats and semantic skins are not independent tasks.",
                "Empirical bootstrap intervals can collapse at all-success/all-failure; they do not prove certainty.",
                "Prompt rescue is sensitivity to this intervention, not an identified intrinsic autonomy trait.",
                "Cost per accepted completion is observed batch cost divided by successes, not a retry forecast.",
                "Token totals are null when any request lacks usage; tokenizers and serving configurations may differ.",
                "No human supervision or real-work predictive validity has been measured by this synthetic suite."]}


def validate_run(directory: Path) -> tuple[dict, list[dict]]:
    from .evaluation import replay
    manifest = json.loads((directory / "private" / "manifest.json").read_text(encoding="utf-8"))
    data = {"generator_version": manifest["generator_version"], "cases": manifest["cases"]}
    if digest(data) != manifest["suite_sha256"]:
        raise ValueError("Suite fingerprint mismatch")
    cases = {digest(c): c for c in manifest["cases"]}
    agents = {a["name"]: a for a in manifest["agents"]}
    if len(cases) != len(manifest["cases"]) or len(agents) != len(manifest["agents"]):
        raise ValueError("Duplicate manifest case or agent")
    expected = {(cid, name, cond, rep) for cid in cases for name in agents
                for cond in manifest["conditions"] for rep in range(manifest["replicates"])}
    if len(expected) != manifest["expected_episodes"]:
        raise ValueError("Invalid expected episode count")
    records, seen = [], set()
    for path in sorted((directory / "private" / "traces").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        key = (record["case_id"], record["agent"]["name"], record["condition"], record["replicate"])
        if key in seen or key not in expected:
            raise ValueError("Duplicate or unexpected trace")
        if record["agent"] != agents[key[1]] or record.get("suite_sha256") != manifest["suite_sha256"]:
            raise ValueError("Trace configuration mismatch")
        case = cases[key[0]]
        if (record["family"], record["profile"], record["domain"]) != (case["family"], case["profile"], case["domain"]):
            raise ValueError("Trace stratum mismatch")
        if record["cluster_id"] != digest([manifest["generator_version"], case["seed"]]):
            raise ValueError("Trace cluster mismatch")
        replay(record, case)
        seen.add(key)
        records.append(record)
    if seen != expected:
        raise ValueError(f"Incomplete run: expected {len(expected)}, found {len(seen)}; missing episodes cannot be dropped")
    return manifest, records
