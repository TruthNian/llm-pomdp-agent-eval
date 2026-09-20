"""Offline falsification fixtures, public-information policies and complete replay."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from .discovery import VERSION, DiscoveryEnvironment, validate_fixture
from .generator import digest
from .storage import read_json

# Public development cases, not random samples or held-out evaluation data.
HANDLE_PAIRS = (("dep-a7", "dep-b2"), ("dep-a7", "dep-q9"), ("dep-m4", "dep-n8"))
POLICIES = ("adaptive", "static", "never_revise", "premature_finish", "overprobe")


def fixtures():
    return [{"handles": list(pair), "visible": visible, "changing": changing}
            for pair in HANDLE_PAIRS for visible in (False, True) for changing in (False, True)]


def public_request(env):
    return {"task": env.contract(), "observation": env.observation(), "history": copy.deepcopy(env.history)}


def control_action(policy, request):
    if policy not in POLICIES:
        raise ValueError("Unknown discovery control")
    observation, history = request["observation"], request["history"]
    if policy == "static":
        # The first action freezes whether a preparation handle was initially known.
        initial = history[0]["action"].get("target") if history else observation["dependency"]
        plan = ([{"command": "prepare", "target": initial}] if initial else []) + [
            {"command": "assemble"}, {"command": "verify"}, {"command": "finish"}]
        return plan[min(len(history), len(plan) - 1)]
    if policy == "overprobe":
        return {"command": "finish" if observation["result"]["kind"] == "budget_blocked" else "probe"}
    if policy == "never_revise" and any(e["observation"]["result"].get("passed") for e in history):
        return {"command": "finish"}
    dependency = observation["dependency"]
    if dependency is None or observation["dependency_stale"]:
        return {"command": "probe"}
    if observation["prepared"] != dependency:
        return {"command": "prepare", "target": dependency}
    if observation["assembly"] != dependency:
        return {"command": "assemble"}
    if policy == "premature_finish":
        return {"command": "finish"}
    for event in reversed(history):
        result = event["observation"]["result"]
        if result.get("passed") and result.get("checked_revision") == observation["revision"]:
            return {"command": "finish"}
    return {"command": "verify"}


def run_control(fixture, policy):
    env = DiscoveryEnvironment(fixture)
    initial = env.observation()
    while not env.done:
        env.step(control_action(policy, public_request(env)))
    return {"version": VERSION, "fixture": copy.deepcopy(fixture), "policy": policy,
            "contract": env.contract(), "initial_observation": initial,
            "events": copy.deepcopy(env.history), "grade": env.grade()}


def accepted_from_public_history(contract, events):
    """Separate observable acceptance check; no environment object, grader or private fixture."""
    if not events or events[-1]["action"] != {"command": "finish"}:
        return False
    final = events[-1]["observation"]
    if (len(events) > contract["max_steps"] or final["remaining"] < 0
            or final["dependency"] is None or final["dependency_stale"]
            or final["prepared"] != final["dependency"] or final["assembly"] != final["dependency"]):
        return False
    return any(e["action"] == {"command": "verify"} and e["observation"]["result"].get("passed")
               and e["observation"]["result"]["checked_revision"] == final["revision"] for e in events)


def replay_control(trace):
    if (not isinstance(trace, dict) or set(trace) != {"version", "fixture", "policy", "contract",
                                                    "initial_observation", "events", "grade"}
            or trace["version"] != VERSION or trace["policy"] not in POLICIES):
        raise ValueError("Unsupported discovery control trace")
    env = DiscoveryEnvironment(trace["fixture"])
    if (digest(trace["initial_observation"]) != digest(env.observation())
            or digest(trace["contract"]) != digest(env.contract())):
        raise ValueError("Discovery contract or initial observation changed")
    if not isinstance(trace["events"], list):
        raise ValueError("Events must be an array")
    for event in trace["events"]:
        if not isinstance(event, dict) or set(event) != {"action", "observation"} or env.done:
            raise ValueError("Invalid or post-terminal event")
        if digest(event["action"]) != digest(control_action(trace["policy"], public_request(env))):
            raise ValueError("Action differs from the declared public-information control")
        if digest(env.step(event["action"])) != digest(event["observation"]):
            raise ValueError("Discovery observation differs from replay")
    if not env.done or digest(trace["grade"]) != digest(env.grade()):
        raise ValueError("Incomplete or inconsistent discovery grade")
    if env.grade()["success"] != accepted_from_public_history(trace["contract"], trace["events"]):
        raise ValueError("State grader and public-history acceptance disagree")
    return env.grade()


def matrix_key(fixture, policy):
    validate_fixture(fixture)
    return (*fixture["handles"], fixture["visible"], fixture["changing"], policy)


def summarize_controls(traces):
    expected = {matrix_key(f, p) for f in fixtures() for p in POLICIES}
    actual = set()
    rows = {(v, c): {"visible": v, "changing": c, "policies": {
        p: {"episodes": 0, "successes": 0, "costs": []} for p in POLICIES}}
        for v in (False, True) for c in (False, True)}
    for trace in traces:
        grade = replay_control(trace)
        fixture, policy = trace["fixture"], trace["policy"]
        key = matrix_key(fixture, policy)
        if key in actual or key not in expected:
            raise ValueError("Duplicate or unplanned discovery control")
        actual.add(key)
        visible, changing = fixture["visible"], fixture["changing"]
        should_pass = (policy == "adaptive" or policy == "static" and visible and not changing
                       or policy == "never_revise" and not changing)
        if grade["success"] != should_pass:
            raise ValueError("Discovery ablation gate failed")
        row = rows[visible, changing]["policies"][policy]
        row["episodes"] += 1
        row["successes"] += int(grade["success"])
        row["costs"].append(grade["cost"])
    if actual != expected:
        raise ValueError("Incomplete discovery control matrix")
    # Order is irrelevant to the fixed matrix; cost distributions remain deterministic.
    for row in rows.values():
        for cell in row["policies"].values():
            cell["costs"].sort()
    return list(rows.values())


def source_hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in ("discovery.py", "discovery_controls.py")}


def make_report():
    traces = [run_control(f, p) for f in fixtures() for p in POLICIES]
    return {"version": VERSION, "source_sha256": source_hashes(), "traces": traces,
            "summary": summarize_controls(traces)}


def validate_report(report):
    if (not isinstance(report, dict) or set(report) != {"version", "source_sha256", "traces", "summary"}
            or report["version"] != VERSION or report["source_sha256"] != source_hashes()
            or not isinstance(report["traces"], list)):
        raise ValueError("Unsupported report or changed prototype source; use the recorded source checkout")
    summary = summarize_controls(report["traces"])
    if digest(report["summary"]) != digest(summary):
        raise ValueError("Discovery summary differs from complete replay")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline discovery/recovery controls; no model calls")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--out", type=Path, help="Write all 60 public development trajectories to a new file")
    operation.add_argument("--validate", type=Path, help="Replay every trajectory and check the full matrix")
    args = parser.parse_args(argv)
    try:
        if args.out is not None:
            if args.out.exists():
                raise ValueError("Output already exists")
            report = make_report()
            validate_report(report)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # This is a disposable offline report, not another durable collector.
            # Exclusive creation also rejects a concurrent writer after the precheck.
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
        else:
            report = read_json(args.validate)
            validate_report(report)
        print(f"Validated {len(report['traces'])} offline controls: discovery/recovery ablations passed. "
              "Public development fixtures; no model or population claims.")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
