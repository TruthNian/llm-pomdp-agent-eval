"""Run manifests, replay, and failure-inclusive data collection."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .agents import AdapterError, make_agent, validate_config
from .environment import CONDITIONS, Environment
from .generator import GENERATOR_VERSION, digest, keyed_seed, validate_case


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_episode(case: dict, config: dict, condition: str, replicate: int, wall_seconds=300) -> dict:
    env = Environment(case, condition, noise_seed=replicate)
    initial = env.observation()
    started = time.monotonic()
    agent, error = None, None
    try:
        # Agent randomization does not depend on the hidden truth or condition.
        agent = make_agent(config, keyed_seed(replicate, "scripted-agent/" + digest(initial)))
        while not env.done:
            remaining = wall_seconds - (time.monotonic() - started)
            if remaining <= 0:
                env.abort("wall_limit")
                break
            request = {"protocol_version": 1, "task": env.contract(), "observation": env.observation(),
                       "history": copy.deepcopy(env.history)}
            action = agent.act(request, timeout=remaining)
            if time.monotonic() - started > wall_seconds:
                env.abort("wall_limit")
                break
            env.step(action)
    except AdapterError as exc:
        error = str(exc)  # Only sanitized adapter exceptions may be recorded.
        env.abort("adapter_error")
    except Exception as exc:
        error = f"Internal adapter/environment error: {type(exc).__name__}"
        env.abort("internal_error")
    baseline = sum(next(c["repair_cost"] for c in stage["candidates"] if c["id"] == truth)
                   for stage, truth in zip(case["stages"], case["truths"])) + case["verify_cost"]
    grade = env.grade()
    return {"schema_version": SCHEMA_VERSION, "framework_version": __version__,
            "case_id": digest(case), "family": case["family"], "profile": case["profile"], "domain": case["domain"],
            "cluster_id": digest([GENERATOR_VERSION, case["seed"]]),
            "agent": copy.deepcopy(config), "condition": condition, "replicate": replicate,
            "initial_observation": initial, "contract": env.contract(), "events": env.history,
            "grade": grade, "error": error, "usage": copy.deepcopy(agent.usage) if agent else None,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "clairvoyant_action_cost_lower_bound": baseline,
            "successful_excess_cost_over_lower_bound": grade["cost"] - baseline if grade["success"] else None}


def replay(trace: dict, case: dict) -> dict:
    if trace.get("schema_version") != SCHEMA_VERSION or trace.get("framework_version") != __version__:
        raise ValueError("Unsupported trace version")
    validate_case(case)
    if trace["case_id"] != digest(case):
        raise ValueError("Trace/case fingerprint mismatch")
    env = Environment(case, trace["condition"], trace["replicate"])
    if trace["initial_observation"] != env.observation() or trace["contract"] != env.contract():
        raise ValueError("Initial observation or contract changed")
    for index, event in enumerate(trace["events"]):
        observed = env.step(event["action"])
        if observed != event["observation"]:
            raise ValueError(f"Replay divergence at step {index + 1}")
    termination = trace["grade"]["termination"]
    if not env.done:
        if termination not in ("adapter_error", "internal_error", "wall_limit"):
            raise ValueError("Missing terminal action")
        env.abort(termination)
    grade = env.grade()
    if grade != trace["grade"]:
        raise ValueError("Recorded grade differs from replayed state")
    return grade


def load_suite(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"generator_version", "cases"} or data.get("generator_version") != GENERATOR_VERSION or not data.get("cases"):
        raise ValueError("Unsupported or empty suite")
    ids = []
    for case in data["cases"]:
        validate_case(case)
        ids.append(digest(case))
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate cases in suite")
    return data


def run_suite(data: dict, configs: list[dict], conditions: list[str], replicates: int,
              output: Path, wall_seconds=300) -> dict:
    if not configs or len({c.get("name") for c in configs}) != len(configs):
        raise ValueError("Agent names must be unique and nonempty")
    for config in configs:
        validate_config(config)
    if not conditions or len(set(conditions)) != len(conditions) or set(conditions) - set(CONDITIONS):
        raise ValueError("Unknown or duplicate conditions")
    if type(replicates) is not int or replicates < 1 or not math.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError("Replicates and wall limit must be positive")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh run directory")
    # Validate all cases before creating a run. No silently dropped cases.
    if set(data) != {"generator_version", "cases"} or data.get("generator_version") != GENERATOR_VERSION or not data.get("cases"):
        raise ValueError("Unsupported or empty suite")
    for case in data["cases"]:
        validate_case(case)
    if len({digest(c) for c in data["cases"]}) != len(data["cases"]):
        raise ValueError("Duplicate cases")
    output.mkdir(parents=True)
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                  timeout=3, cwd=Path(__file__).resolve().parents[1]).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                                   timeout=3, cwd=Path(__file__).resolve().parents[1]).stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        revision, dirty = None, None
    source_files = sorted(Path(__file__).resolve().parent.glob("*.py"))
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    manifest = {"schema_version": SCHEMA_VERSION, "framework_version": __version__,
                "generator_version": GENERATOR_VERSION, "suite_sha256": digest(data),
                "agents": configs, "conditions": conditions, "replicates": replicates,
                "wall_seconds_per_episode": wall_seconds, "python": sys.version,
                "platform": platform.platform(), "git_revision": revision, "working_tree_dirty": dirty,
                "source_sha256": source_hashes,
                "created_at": datetime.now(timezone.utc).isoformat(), "cases": data["cases"],
                "expected_episodes": len(data["cases"]) * len(configs) * len(conditions) * replicates}
    write_json(output / "private" / "manifest.json", manifest)
    records = []
    # Rotate agent order between cases; no named model is privileged in the runner.
    for i, case in enumerate(data["cases"]):
        order = configs[i % len(configs):] + configs[:i % len(configs)]
        for replicate in range(replicates):
            for condition in conditions:
                for config in order:
                    record = run_episode(case, config, condition, replicate, wall_seconds)
                    record["suite_sha256"] = manifest["suite_sha256"]
                    replay(record, case)
                    name = digest([record["case_id"], config["name"], condition, replicate])
                    write_json(output / "private" / "traces" / f"{name}.json", record)
                    records.append(record)
    from .reporting import summarize
    report = summarize(records)
    report["run"] = {k: v for k, v in manifest.items() if k != "cases"}
    report["complete"] = len(records) == manifest["expected_episodes"]
    write_json(output / "summary.json", report)
    return report
