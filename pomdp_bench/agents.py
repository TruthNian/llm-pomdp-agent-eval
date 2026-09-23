"""Adapters receive public JSON only. The HTTP adapter exposes no shell or files."""
from __future__ import annotations

import json
import copy
import math
import random

from .model_io import AdapterError, ChatAgent, ResponsesAgent, response_byte_limit, strict_json
from .planning import consistent_candidates, diagnostic_plan
from .interventions import RESERVE_TEXT
from . import version_at_least
from .coverage import POLICIES as COVER_POLICIES, ASSISTED_POLICIES, policy_action as cover_action
from .incident import POLICY as INCIDENT_POLICY, policy_action as incident_action

from .settlement import POLICY as SETTLEMENT_POLICY, policy_action as settlement_action

from .reconciliation import POLICY as RECONCILIATION_POLICY
from .reconciliation_control import policy_action as reconciliation_action

from .refund_recovery import POLICY as REFUND_POLICY
from .refund_control import policy_action as refund_action

BUILTINS = ("reference", "random", "overdiagnose", "proxy")
POLICIES = (*BUILTINS, "reserve_probe", *COVER_POLICIES, *ASSISTED_POLICIES, INCIDENT_POLICY, SETTLEMENT_POLICY, RECONCILIATION_POLICY, REFUND_POLICY)


def validate_config(config: dict) -> None:
    allowed = {"name", "kind", "model", "endpoint_env", "api_key_env", "options",
               "timeout_seconds", "headers_env", "max_response_bytes", "actions"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("Unknown agent configuration fields")
    if not isinstance(config.get("name"), str) or not config["name"].strip():
        raise ValueError("Every agent needs a nonempty name")
    if config.get("kind") not in (*POLICIES, "chat", "responses", "responses_tools", "responses_session", "actions"):
        raise ValueError("Unknown agent kind")
    if config["kind"] == "actions":
        if (set(config) != {"name", "kind", "actions"} or not isinstance(config["actions"], list)
                or not config["actions"] or len(config["actions"]) > 100):
            raise ValueError("Fixed-action artifact controls require 1-100 explicit actions")
    elif "actions" in config:
        raise ValueError("Only fixed-action controls accept an action sequence")
    if "max_response_bytes" in config:
        if config["kind"] not in ("chat", "responses", "responses_tools", "responses_session"):
            raise ValueError("max_response_bytes applies only to HTTP agents")
        response_byte_limit(config)
    if config["kind"] in ("chat", "responses", "responses_tools", "responses_session"):
        for field in ("model", "endpoint_env", "api_key_env"):
            if not isinstance(config.get(field), str) or not config[field]:
                raise ValueError(f"HTTP adapter requires {field}")
        if "headers_env" in config and (not isinstance(config["headers_env"], str) or not config["headers_env"]):
            raise ValueError("headers_env must name an environment variable")
        options = config.get("options", {})
        allowed_options = ({"temperature", "top_p", "reasoning_effort", "max_output_tokens"}
                           if config["kind"] in ("responses", "responses_tools", "responses_session") else
                           {"temperature", "top_p", "max_tokens", "max_completion_tokens", "reasoning_effort", "seed"})
        if not isinstance(options, dict) or set(options) - allowed_options:
            raise ValueError("Unsupported request option; model, messages, tools, and credentials are adapter-owned")
        for key, value in options.items():
            if key == "reasoning_effort":
                if value not in ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"):
                    raise ValueError("Unknown reasoning_effort")
            elif type(value) not in (int, float):
                raise ValueError("Sampling and token options must be numeric")
    timeout = config.get("timeout_seconds", 30)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Request timeout must be finite and positive; the episode wall limit still applies")
    json.dumps(config, allow_nan=False)


def validate_agent_version(config, version):
    if config["kind"] == "responses_session" and not version_at_least(version, "2.16.0"):
        raise ValueError("Continuous native sessions require framework 2.16")
    if config["kind"] == "responses_tools" and not version_at_least(version, "2.14.0"):
        raise ValueError("Native takeover tools require framework 2.14")
    if config["kind"] == REFUND_POLICY and not version_at_least(version, "2.12.0"):
        raise ValueError("Refund operator requires framework 2.12")
    if config["kind"] == RECONCILIATION_POLICY and not version_at_least(version, "2.11.0"):
        raise ValueError("Reconciliation operator requires framework 2.11")
    if config["kind"] == SETTLEMENT_POLICY and not version_at_least(version, "2.10.0"):
        raise ValueError("Settlement operator requires framework 2.10")
    if config["kind"] == INCIDENT_POLICY and not version_at_least(version, "2.9.0"):
        raise ValueError("Incident operator requires framework 2.9")
    if config["kind"] == "actions" and not version_at_least(version, "2.7.0"):
        raise ValueError("Fixed-action artifact controls require framework 2.7")
    if "max_response_bytes" in config and not version_at_least(version, "2.5.2"):
        raise ValueError("Explicit response byte limits require framework 2.5.2")
    if config["kind"] in COVER_POLICIES and not version_at_least(version, "2.5.0"):
        raise ValueError("Coverage policies require framework 2.5")
    if config["kind"] in ASSISTED_POLICIES and not version_at_least(version, "2.6.0"):
        raise ValueError("Solver consumer policy requires framework 2.6")
    if version in ("2.0.0", "2.1.0", "2.2.0") and (config["kind"] == "responses" or "headers_env" in config):
        raise ValueError("This HTTP configuration requires framework 2.3 or later")


class ScriptedAgent:
    def __init__(self, kind: str, seed: int):
        self.kind = kind
        self.rng = random.Random(seed)
        self.usage = None  # No model tokens were consumed; never fabricate zero-token LLM measurements.

    def act(self, request: dict, timeout: float) -> dict:
        if self.kind == REFUND_POLICY:
            return refund_action(request)
        if self.kind == RECONCILIATION_POLICY:
            return reconciliation_action(request)
        if self.kind == SETTLEMENT_POLICY:
            return settlement_action(request)
        if self.kind == INCIDENT_POLICY:
            return incident_action(request)
        if request["task"].get("family") == "dependency_cover":
            return cover_action("cover_reference" if self.kind == "reference" else self.kind, request)
        observation, history = request["observation"], request["history"]
        if self.kind == "proxy":
            return {"command": "override", "target": "on"} if not history else {"command": "finish"}
        if self.kind == "random":
            actions = [{"command": "finish"}, {"command": "verify"}, {"command": "rollback"}]
            if observation["catalogue"]:
                actions += [{"command": "inspect", "target": t["id"]} for t in observation["catalogue"]["tests"]]
                actions += [{"command": "repair", "target": c["id"]} for c in observation["catalogue"]["candidates"]]
            return self.rng.choice(actions)
        if observation["override_active"]:
            return {"command": "override", "target": "off"}
        if observation["collateral_damage"]:
            return {"command": "rollback"}
        if observation["workflow_complete"]:
            last = observation["result"]
            if self.kind == "reserve_probe" and last.get("kind") == "blocked":
                return {"command": "finish"}
            return {"command": "finish"} if last.get("kind") == "verify" and last.get("passed") else {"command": "verify"}
        if self.kind == "overdiagnose":
            # Deliberate negative control: inspect the entire checklist twice before acting.
            if observation["result"].get("kind") == "blocked":
                return {"command": "finish"}
            phase = observation["phase"]
            n = sum(e["observation"]["result"].get("kind") == "test" and
                    e["observation"]["result"].get("phase") == phase for e in history)
            tests = observation["catalogue"]["tests"]
            if n < 2 * len(tests):
                return {"command": "inspect", "target": tests[n % len(tests)]["id"]}
        possible = consistent_candidates(observation, history)
        if self.kind == "reserve_probe" and len(possible) == 1:
            # Constructed sensitivity control: unnecessary checks preserve repair costs,
            # but reserve final verification ONLY when the public reminder is present.
            stage = observation["catalogue"]
            repair = next(c["repair_cost"] for c in stage["candidates"] if c["id"] in possible)
            reserve = repair + observation["future_cost_bound"]
            if RESERVE_TEXT in request["task"]["task"]:
                reserve += request["task"]["verify_cost"]
            names = {c["id"] for c in stage["candidates"]}
            irrelevant = min((t for t in stage["tests"] if t["accuracy"] == 1
                              and set(t["positive_for"]) == names), key=lambda t: (t["cost"], t["id"]))
            if observation["remaining"] >= reserve + irrelevant["cost"]:
                return {"command": "inspect", "target": irrelevant["id"]}
        return diagnostic_plan(observation["catalogue"], possible)[1]


def make_agent(config: dict, seed: int):
    validate_config(config)
    if config["kind"] == "actions":
        return ActionSequence(config["actions"])
    return ChatAgent(config) if config["kind"] in ("chat", "responses", "responses_tools", "responses_session") else ScriptedAgent(config["kind"], seed)


class ActionSequence:
    """An explicitly supplied artifact control, never presented as a solving agent."""
    usage = None

    def __init__(self, actions):
        self.actions = iter(copy.deepcopy(actions))

    def act(self, request, timeout):
        return next(self.actions, {"command": "finish"})
