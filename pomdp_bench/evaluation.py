"""Public-information episodes, durable checkpoints, and deterministic replay."""
from __future__ import annotations

import copy
import time
from pathlib import Path

from . import REPLAY_VERSIONS, SCHEMA_VERSION, __version__
from .agents import AdapterError, make_agent
from .environment import Environment
from .generator import GENERATOR_VERSION, digest, keyed_seed, validate_case
from .storage import read_json, write_json


def episode_record(env, config, replicate, elapsed=0, usage=None, error=None, in_flight=False):
    case = env.case
    baseline = sum(next(c["repair_cost"] for c in stage["candidates"] if c["id"] == truth)
                   for stage, truth in zip(case["stages"], case["truths"])) + case["verify_cost"]
    grade = env.grade()
    return {"schema_version": SCHEMA_VERSION, "framework_version": __version__,
            "case_id": digest(case), "family": case["family"], "profile": case["profile"], "domain": case["domain"],
            "cluster_id": digest([GENERATOR_VERSION, case["seed"]]),
            "agent": copy.deepcopy(config), "condition": env.condition, "replicate": replicate,
            "initial_observation": Environment(case, env.condition, replicate).observation(),
            "contract": env.contract(), "events": copy.deepcopy(env.history),
            "grade": grade, "error": error, "usage": copy.deepcopy(usage),
            "request_in_flight": in_flight, "elapsed_seconds": round(elapsed, 6),
            "clairvoyant_action_cost_lower_bound": baseline,
            "successful_excess_cost_over_lower_bound": grade["cost"] - baseline if grade["success"] else None}


def run_episode(case: dict, config: dict, condition: str, replicate: int, wall_seconds=300,
                checkpoint=None) -> dict:
    env = Environment(case, condition, noise_seed=replicate)
    started = time.monotonic()
    agent, error, in_flight = None, None, False

    def snapshot():
        record = episode_record(env, config, replicate, time.monotonic() - started,
                                agent.usage if agent else None, error, in_flight)
        # Storage failures must stop collection, never masquerade as model failures.
        if checkpoint:
            checkpoint(record)
        return record

    snapshot()
    try:
        agent = make_agent(config, keyed_seed(replicate, "scripted-agent/" + digest(env.observation())))
    except AdapterError as exc:
        error = str(exc)
        env.abort("adapter_error")
    except Exception as exc:
        error = f"Internal adapter/environment error: {type(exc).__name__}"
        env.abort("internal_error")
    while not env.done:
        remaining = wall_seconds - (time.monotonic() - started)
        if remaining <= 0:
            env.abort("wall_limit")
            break
        request = {"protocol_version": 1, "task": env.contract(), "observation": env.observation(),
                   "history": copy.deepcopy(env.history)}
        in_flight = True
        snapshot()  # Persist uncertainty BEFORE a potentially billable request.
        remaining = wall_seconds - (time.monotonic() - started)
        if remaining <= 0:
            in_flight = False
            env.abort("wall_limit")
            break
        try:
            action = agent.act(request, timeout=remaining)
            if time.monotonic() - started > wall_seconds:
                env.abort("wall_limit")
            else:
                env.step(action)
        except AdapterError as exc:
            error = str(exc)  # Only sanitized adapter exceptions may be recorded.
            env.abort("adapter_error")
        except Exception as exc:
            error = f"Internal adapter/environment error: {type(exc).__name__}"
            env.abort("internal_error")
        in_flight = False
        snapshot()
    return snapshot()


def replay_environment(trace: dict, case: dict, *, partial=False) -> Environment:
    if trace.get("schema_version") != SCHEMA_VERSION or trace.get("framework_version") not in REPLAY_VERSIONS:
        raise ValueError("Unsupported trace version")
    validate_case(case)
    if trace["case_id"] != digest(case):
        raise ValueError("Trace/case fingerprint mismatch")
    env = Environment(case, trace["condition"], trace["replicate"])
    if trace["initial_observation"] != env.observation() or trace["contract"] != env.contract():
        raise ValueError("Initial observation or contract changed")
    for index, event in enumerate(trace["events"]):
        if env.step(event["action"]) != event["observation"]:
            raise ValueError(f"Replay divergence at step {index + 1}")
    termination = trace["grade"]["termination"]
    if not env.done and not (partial and termination is None):
        allowed = {"adapter_error", "internal_error", "wall_limit"}
        if trace["framework_version"] != "2.0.0":
            allowed.add("collection_interrupted")
        if termination not in allowed:
            raise ValueError("Missing terminal action")
        env.abort(termination)
    if env.grade() != trace["grade"]:
        raise ValueError("Recorded grade differs from replayed state")
    baseline = episode_record(env, trace["agent"], trace["replicate"])
    for field in ("clairvoyant_action_cost_lower_bound", "successful_excess_cost_over_lower_bound"):
        if trace.get(field) != baseline[field]:
            raise ValueError("Recorded cost bound differs from replayed state")
    return env


def replay(trace: dict, case: dict) -> dict:
    return replay_environment(trace, case).grade()


def recover_interrupted(checkpoint: dict, case: dict) -> dict:
    """Preserve terminal evidence; otherwise fail the attempt, never call the agent again."""
    env = replay_environment(checkpoint, case, partial=True)
    record = copy.deepcopy(checkpoint)
    if not env.done:
        env.abort("collection_interrupted")
        record.update(grade=env.grade(), error="Collection interrupted; episode was not retried",
                      partial_usage=record["usage"], usage=None,
                      elapsed_seconds_is_lower_bound=True, successful_excess_cost_over_lower_bound=None)
    record["recovered_from_checkpoint"] = True
    replay(record, case)
    return record


def validate_suite(data: dict) -> None:
    if (not isinstance(data, dict) or set(data) != {"generator_version", "cases"}
            or data.get("generator_version") != GENERATOR_VERSION or not data.get("cases")):
        raise ValueError("Unsupported or empty suite")
    ids = []
    for case in data["cases"]:
        validate_case(case)
        ids.append(digest(case))
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate cases in suite")


def load_suite(path: Path) -> dict:
    data = read_json(path)
    validate_suite(data)
    return data
