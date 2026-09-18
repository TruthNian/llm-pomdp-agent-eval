"""One immutable matrix, one attempt per episode, and no implicit retries."""
from __future__ import annotations

import hashlib
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import REPLAY_VERSIONS, SCHEMA_VERSION, __version__
from .agents import validate_agent_version, validate_config
from .environment import CONDITIONS, Environment, validate_condition_version
from .evaluation import episode_record, recover_interrupted, replay, replay_environment, run_episode, validate_suite
from .generator import digest
from .storage import collection_lock, read_json, write_json

COLLECTION_VERSION = 1


def source_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).resolve().parent.glob("*.py"))}


def validate_definition(data, configs, conditions, replicates, wall_seconds):
    validate_suite(data)
    if not isinstance(configs, list) or not configs:
        raise ValueError("Agents must be a nonempty array")
    for config in configs:
        validate_config(config)
    if len({c["name"] for c in configs}) != len(configs):
        raise ValueError("Agent names must be unique")
    if (not isinstance(conditions, list) or not conditions or len(set(conditions)) != len(conditions)
            or set(conditions) - set(CONDITIONS)):
        raise ValueError("Unknown or duplicate conditions")
    if (type(replicates) is not int or replicates < 1 or type(wall_seconds) not in (int, float)
            or not math.isfinite(wall_seconds) or wall_seconds <= 0):
        raise ValueError("Replicates and wall limit must be positive")


def schedule(manifest):
    entries = []
    configs = manifest["agents"]
    if "study" in manifest:
        # Adjacent pairs reduce drift; first condition is counterbalanced by seed,
        # replicate and stable agent index. No hidden answer influences this order.
        seeds = list(dict.fromkeys(c["seed"] for c in manifest["cases"]))
        seed_index = {seed: i for i, seed in enumerate(seeds)}
        for i, case in enumerate(manifest["cases"]):
            for replicate in range(manifest["replicates"]):
                order = list(range(len(configs)))
                offset = (i + replicate) % len(configs)
                order = order[offset:] + order[:offset]
                for agent_index in order:
                    conditions = manifest["conditions"]
                    if (seed_index[case["seed"]] + replicate + agent_index) % 2:
                        conditions = list(reversed(conditions))
                    for condition in conditions:
                        cid, name = digest(case), configs[agent_index]["name"]
                        entries.append({"episode_id": digest([cid, name, condition, replicate]),
                                        "case_id": cid, "agent": name, "condition": condition,
                                        "replicate": replicate})
        return entries
    for i, case in enumerate(manifest["cases"]):
        order = configs[i % len(configs):] + configs[:i % len(configs)]
        for replicate in range(manifest["replicates"]):
            for condition in manifest["conditions"]:
                for config in order:
                    cid = digest(case)
                    entries.append({"episode_id": digest([cid, config["name"], condition, replicate]),
                                    "case_id": cid, "agent": config["name"],
                                    "condition": condition, "replicate": replicate})
    return entries


def prepare_suite(data, configs, conditions, replicates, output: Path, wall_seconds=300, *, study=None):
    validate_definition(data, configs, conditions, replicates, wall_seconds)
    if study is not None:
        from .studies import validate_binding
        validate_binding(study, data, configs, conditions, replicates, wall_seconds)
        if study["plan"]["framework_version"] != __version__:
            raise ValueError("Study framework version differs from collector")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh run directory")
    try:
        root = Path(__file__).resolve().parents[1]
        revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                  timeout=3, cwd=root).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                                   timeout=3, cwd=root).stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        revision, dirty = None, None
    manifest = {"schema_version": SCHEMA_VERSION, "framework_version": __version__,
                "collection_version": COLLECTION_VERSION, "generator_version": data["generator_version"],
                "suite_sha256": digest(data), "agents": configs, "conditions": conditions, "replicates": replicates,
                "wall_seconds_per_episode": wall_seconds, "python": sys.version, "platform": platform.platform(),
                "git_revision": revision, "working_tree_dirty": dirty, "source_sha256": source_hashes(),
                "created_at": datetime.now(timezone.utc).isoformat(), "cases": data["cases"],
                "expected_episodes": len(data["cases"]) * len(configs) * len(conditions) * replicates}
    if study is not None:
        manifest["study"] = study
    manifest["schedule_sha256"] = digest(schedule(manifest))
    output.mkdir(parents=True)
    with collection_lock(output):
        write_json(output / "private" / "manifest.json", manifest, replace=False)
        write_json(output / "private" / "manifest.sha256.json", {"sha256": digest(manifest)}, replace=False)
    return manifest


def _paths(directory, kind):
    return {p.stem: p for p in (directory / "private" / kind).glob("*.json")}


def read_run(directory: Path, *, partial=False):
    """Validate all existing evidence; partial permits absent uncommitted episodes only."""
    manifest = read_json(directory / "private" / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("framework_version") not in REPLAY_VERSIONS:
        raise ValueError("Unsupported manifest version")
    for condition in manifest["conditions"]:
        validate_condition_version(condition, manifest["framework_version"])
    for config in manifest["agents"]:
        validate_agent_version(config, manifest["framework_version"])
    data = {"generator_version": manifest["generator_version"], "cases": manifest["cases"]}
    validate_definition(data, manifest["agents"], manifest["conditions"], manifest["replicates"],
                        manifest["wall_seconds_per_episode"])
    if "study" in manifest:
        from .studies import validate_binding
        validate_binding(manifest["study"], data, manifest["agents"], manifest["conditions"],
                         manifest["replicates"], manifest["wall_seconds_per_episode"])
        if manifest["framework_version"] != manifest["study"]["plan"]["framework_version"]:
            raise ValueError("Study framework version differs from manifest")
    if digest(data) != manifest["suite_sha256"]:
        raise ValueError("Suite fingerprint mismatch")
    entries = schedule(manifest)
    expected = {entry["episode_id"]: entry for entry in entries}
    if len(expected) != manifest["expected_episodes"]:
        raise ValueError("Invalid expected episode count")
    version = manifest.get("collection_version")
    if version is not None and version != COLLECTION_VERSION:
        raise ValueError("Unsupported collection version")
    if manifest["framework_version"] != "2.0.0" and version is None:
        raise ValueError("Missing collection version")
    if version and digest(entries) != manifest.get("schedule_sha256"):
        raise ValueError("Schedule fingerprint mismatch")
    if version and read_json(directory / "private" / "manifest.sha256.json") != {"sha256": digest(manifest)}:
        raise ValueError("Prepared manifest mismatch")
    cases = {digest(c): c for c in data["cases"]}
    agents = {a["name"]: a for a in manifest["agents"]}
    traces, starts, receipts, checkpoints = (_paths(directory, kind) for kind in
                                            ("traces", "starts", "receipts", "checkpoints"))
    for paths in (traces, starts, receipts, checkpoints):
        if paths.keys() - expected.keys():
            raise ValueError("Unexpected episode evidence")
    if version:
        if (traces.keys() | receipts.keys() | checkpoints.keys()) - starts.keys():
            raise ValueError("Evidence without an immutable start record")
        if receipts.keys() - traces.keys():
            raise ValueError("Incomplete committed evidence: a receipted trace is missing")
        fingerprint = digest(manifest)
        for eid, path in starts.items():
            start = read_json(path)
            if (set(start) != {"episode_id", "manifest_sha256", "started_at"}
                    or start["episode_id"] != eid or start["manifest_sha256"] != fingerprint):
                raise ValueError("Start record/manifest mismatch")
        for eid, path in receipts.items():
            receipt = read_json(path)
            if receipt != {"episode_id": eid, "manifest_sha256": fingerprint,
                           "trace_sha256": digest(read_json(traces[eid]))}:
                raise ValueError("Committed trace/receipt mismatch")

    def check_record(record, eid, *, checkpoint=False):
        entry = expected[eid]
        if (record["case_id"] != entry["case_id"] or record["agent"] != agents[entry["agent"]]
                or record["condition"] != entry["condition"] or record["replicate"] != entry["replicate"]
                or record.get("suite_sha256") != manifest["suite_sha256"]
                or record.get("framework_version") != manifest["framework_version"]):
            raise ValueError("Trace configuration or version mismatch")
        case = cases[entry["case_id"]]
        if any(record[k] != case[k] for k in ("family", "profile", "domain")):
            raise ValueError("Trace stratum mismatch")
        if record["cluster_id"] != digest([manifest["generator_version"], case["seed"]]):
            raise ValueError("Trace cluster mismatch")
        if version and type(record.get("request_in_flight")) is not bool:
            raise ValueError("Missing request boundary evidence")
        if not checkpoint and record.get("request_in_flight") and record["grade"]["termination"] != "collection_interrupted":
            raise ValueError("Unresolved request in a terminal trace")
        replay_environment(record, case, partial=checkpoint)

    records, by_id = [], {}
    for eid, path in sorted(traces.items()):
        record = read_json(path)
        check_record(record, eid)
        records.append(record)
        by_id[eid] = record
    for eid, path in checkpoints.items():
        checkpoint = read_json(path)
        check_record(checkpoint, eid, checkpoint=True)
        if eid in by_id and checkpoint["events"] != by_id[eid]["events"][:len(checkpoint["events"])]:
            raise ValueError("Checkpoint is not a prefix of its committed trajectory")
    if not partial and (traces.keys() != expected.keys() or (version and receipts.keys() != expected.keys())):
        raise ValueError(f"Incomplete run: expected {len(expected)}, found {len(traces)}; missing episodes cannot be dropped")
    return manifest, records


def run_status(directory: Path):
    with collection_lock(directory):
        manifest, records = read_run(directory, partial=True)
        versioned = manifest.get("collection_version")
        started = len(_paths(directory, "starts")) if versioned else len(records)
        completed = len(_paths(directory, "receipts")) if versioned else len(records)
        return {"expected": manifest["expected_episodes"], "completed": completed,
                "interrupted_unsealed": started - completed,
                "pending": manifest["expected_episodes"] - started,
                "collection_failures": sum(r["grade"]["termination"] == "collection_interrupted" for r in records),
                "framework_version": manifest["framework_version"], "suite_sha256": manifest["suite_sha256"]}


def save_summary(directory: Path):
    from .reporting import summarize
    manifest, records = read_run(directory)
    report = summarize(records, compare_agents="study" not in manifest)
    if "study" in manifest:
        from .studies import analyze_study
        report["study_analysis"] = analyze_study(manifest, records)
    report["run"] = {k: v for k, v in manifest.items() if k != "cases"}
    report["complete"] = True
    write_json(directory / "summary.json", report)
    return report


def resume_suite(directory: Path):
    if not (directory / "private" / "manifest.json").is_file():
        raise ValueError("Run manifest not found")
    with collection_lock(directory):
        manifest, records = read_run(directory, partial=True)
        if (manifest.get("collection_version") != COLLECTION_VERSION
                or manifest["framework_version"] != __version__
                or manifest["source_sha256"] != source_hashes()
                or manifest["python"] != sys.version or manifest["platform"] != platform.platform()):
            raise ValueError("Resume requires the original collection version, source files, Python and platform")
        cases = {digest(c): c for c in manifest["cases"]}
        agents = {a["name"]: a for a in manifest["agents"]}
        existing = {digest([r["case_id"], r["agent"]["name"], r["condition"], r["replicate"]]): r for r in records}
        fingerprint = digest(manifest)
        for entry in schedule(manifest):
            eid = entry["episode_id"]
            case, config = cases[entry["case_id"]], agents[entry["agent"]]
            private = directory / "private"
            start_path = private / "starts" / f"{eid}.json"
            trace_path = private / "traces" / f"{eid}.json"
            checkpoint_path = private / "checkpoints" / f"{eid}.json"
            receipt_path = private / "receipts" / f"{eid}.json"
            if eid in existing:
                record = existing[eid]
            else:
                if start_path.exists():
                    snapshot = read_json(checkpoint_path) if checkpoint_path.exists() else episode_record(
                        Environment(case, entry["condition"], entry["replicate"]), config, entry["replicate"])
                    record = recover_interrupted(snapshot, case)
                else:
                    write_json(start_path, {"episode_id": eid, "manifest_sha256": fingerprint,
                                           "started_at": datetime.now(timezone.utc).isoformat()}, replace=False)

                    def checkpoint(record):
                        record["suite_sha256"] = manifest["suite_sha256"]
                        write_json(checkpoint_path, record)

                    record = run_episode(case, config, entry["condition"], entry["replicate"],
                                         manifest["wall_seconds_per_episode"], checkpoint=checkpoint)
                record["suite_sha256"] = manifest["suite_sha256"]
                replay(record, case)
                write_json(trace_path, record, replace=False)
            if not receipt_path.exists():
                write_json(receipt_path, {"episode_id": eid, "manifest_sha256": fingerprint,
                                         "trace_sha256": digest(record)}, replace=False)
        return save_summary(directory)


def run_suite(data, configs, conditions, replicates, output: Path, wall_seconds=300):
    prepare_suite(data, configs, conditions, replicates, output, wall_seconds)
    return resume_suite(output)
