"""One-shot stream incident through Boyue's ordinary Chat Completions tools.

Each invocation owns one isolated Docker incident. Full assistant/tool dialogue,
including any provider reasoning field, stays in memory; public evidence retains
only hashes, tool actions, observations, usage and the independent business grade.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from pomdp_bench import __version__
from pomdp_bench.generator import digest
from pomdp_bench.model_io import strict_json
from pomdp_bench.stream import StreamEnvironment, suite
from pomdp_bench.stream_runtime import configuration


TOOLS = [
    {"type": "function", "function": {"name": "exec", "description": "Run a Bash script in the authorized operations environment.",
      "parameters": {"type": "object", "properties": {"target": {"type": "string"}},
                     "required": ["target"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "finish", "description": "Hand over the service and end interaction.",
      "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def registration() -> tuple[str, str]:
    """Return the GLM registration's Boyue base and key, without writing either."""
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "codex-router"
    models = json.loads((root / "user-models.json").read_text(encoding="utf-8"))["models"]
    entry = next(item for item in models if item["slug"] == "custom/z-ai/glm-5.3")
    endpoint = entry["endpoint"]
    return endpoint["baseUrl"].rstrip("/"), (root / endpoint["credential"]["file"]).read_text(encoding="utf-8").strip()


def exchange(url: str, key: str, payload: dict, audit: dict, *, timeout: float, byte_limit: int) -> dict:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
    request = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json"})
    audit.update(request_sha256=sha256(body), request_bytes=len(body), outcome="in_flight")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            audit["http_status"] = response.status
            raw = response.read(byte_limit + 1)
        if len(raw) > byte_limit:
            raise ValueError("response_too_large")
        data = strict_json(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid_response_object")
        audit.update(response_sha256=sha256(raw), response_bytes=len(raw), outcome="response")
        return data
    except urllib.error.HTTPError as exc:
        audit.update(http_status=exc.code, outcome="http_error")
        raise RuntimeError("http_error") from None
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        audit["outcome"] = "timeout" if isinstance(exc, TimeoutError) else "transport_error"
        raise RuntimeError(audit["outcome"]) from None
    finally:
        audit["elapsed_seconds"] = round(time.monotonic() - started, 6)


def native_action(data: dict, expected_model: str) -> tuple[dict | None, dict, dict]:
    if data.get("model") != expected_model:
        raise ValueError("returned_model_mismatch")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("invalid_choices")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ValueError("invalid_assistant_message")
    calls = message.get("tool_calls") or []
    if not calls and choice.get("finish_reason") == "stop":
        return None, message, {"finish_reason": "stop", "tool_calls": 0}
    if choice.get("finish_reason") != "tool_calls" or len(calls) != 1:
        raise ValueError("invalid_tool_count_or_finish")
    call = calls[0]
    if call.get("type") != "function" or not isinstance(call.get("id"), str) or not call["id"]:
        raise ValueError("invalid_tool_call_id")
    function = call.get("function")
    if not isinstance(function, dict) or function.get("name") not in ("exec", "finish"):
        raise ValueError("undeclared_tool")
    arguments = strict_json(function.get("arguments", ""))
    if function["name"] == "exec" and isinstance(arguments, dict) and set(arguments) == {"target"} and isinstance(arguments["target"], str):
        action = {"command": "exec", "target": arguments["target"]}
    elif function["name"] == "finish" and arguments == {}:
        action = {"command": "finish"}
    else:
        action = {"command": "invalid_model_output"}
    # DeepSeek's thinking-mode chat protocol requires non-null assistant content;
    # preserve every provider-specific field (especially reasoning_content).
    message = copy.deepcopy(message)
    message["content"] = message.get("content") or ""
    return action, message, {"finish_reason": "tool_calls", "tool_calls": 1, "tool_name": function["name"]}


def update_usage(total: dict, reported: object) -> None:
    if not isinstance(reported, dict):
        return
    inputs, outputs = reported.get("prompt_tokens"), reported.get("completion_tokens")
    if type(inputs) is not int or type(outputs) is not int or inputs < 0 or outputs < 0:
        return
    total["reports"] += 1
    total["input_tokens"] += inputs
    total["output_tokens"] += outputs
    details = reported.get("completion_tokens_details")
    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
    if type(reasoning) is int and reasoning >= 0:
        total["reasoning_reports"] += 1
        total["reasoning_tokens"] += reasoning


def run(plan_path: Path, model: str, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("One-shot output path already exists")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["framework_version"] != __version__ or model not in plan["models"]:
        raise ValueError("Model or framework is outside the frozen plan")
    for relative, expected in plan["source_sha256"].items():
        if sha256((Path(__file__).resolve().parents[1] / relative).read_bytes()) != expected:
            raise ValueError("Frozen source changed: " + relative)
    if digest(suite()) != plan["suite_sha256"]:
        raise ValueError("Frozen suite changed")
    runtime = configuration()
    if any(runtime.get(field) != value for field, value in plan["runtime"].items()):
        raise ValueError("Frozen runtime changed")
    base, key = registration()
    if base != plan["transport"]["base_url"] or not key:
        raise ValueError("Boyue registration changed")
    output.mkdir(parents=True)
    case = suite()["cases"][0]
    env = StreamEnvironment(case)
    initial = env.observation()
    contract = env.contract()
    messages = [{"role": "system", "content": "Follow the task contract. Use the available tools to act."},
                {"role": "user", "content": json.dumps({"protocol_version": 1, "task": contract,
                                                        "observation": initial, "history": []}, ensure_ascii=False)}]
    usage = {"requests": 0, "reports": 0, "input_tokens": 0, "output_tokens": 0,
             "reasoning_reports": 0, "reasoning_tokens": 0}
    audits = []
    started = time.monotonic()
    error = None
    phase = "environment_start"

    def snapshot():
        record = {"study_id": plan["study_id"], "plan_sha256": sha256(plan_path.read_bytes()),
                  "model": model, "interface": "boyue-chat-tools/1", "case": case,
                  "contract": contract, "initial_observation": initial,
                  "events": copy.deepcopy(env.history), "service_evidence": env.evidence(),
                  "grade": env.grade(), "usage": copy.deepcopy(usage),
                  "request_audit": copy.deepcopy(audits), "phase": phase, "error": error,
                  "elapsed_seconds": round(time.monotonic() - started, 6)}
        save(output / "checkpoint.json", record)
        return record

    try:
        snapshot()
        env.start()
        phase = "agent_turn"
        while not env.done:
            remaining = plan["limits"]["wall_seconds"] - (time.monotonic() - started)
            if remaining <= 0:
                error = "wall_limit"
                env.abort("wall_limit")
                break
            payload = {"model": model, "messages": messages, "tools": TOOLS, "stream": False}
            audit = {"outcome": "in_flight"}
            audits.append(audit)
            usage["requests"] += 1
            snapshot()
            try:
                response = exchange(base + "/chat/completions", key, payload, audit,
                                    timeout=min(remaining, plan["limits"]["request_seconds"]),
                                    byte_limit=plan["limits"]["response_bytes"])
                update_usage(usage, response.get("usage"))
                action, assistant, parsed = native_action(response, model)
                audit.update(parsed, returned_model=response.get("model"), outcome="action" if action else "agent_stopped")
            except Exception as exc:
                error = type(exc).__name__ + ":" + (str(exc) if isinstance(exc, (RuntimeError, ValueError)) else "protocol_error")
                audit["outcome"] = error
                env.abort("adapter_error")
                break
            if action is None:
                error = "Agent ended without calling finish"
                env.abort("agent_stopped")
                break
            observation = env.step(action)
            messages.append(assistant)
            messages.append({"role": "tool", "tool_call_id": assistant["tool_calls"][0]["id"],
                             "content": json.dumps(observation, ensure_ascii=False, allow_nan=False)})
            snapshot()
            print(json.dumps({"model": model, "step": len(env.history), "tool": action["command"],
                              "done": env.done, "elapsed_seconds": round(time.monotonic() - started, 1)}), flush=True)
        return snapshot()
    except Exception as exc:
        error = "Local integration failure at " + phase + ":" + type(exc).__name__
        if not env.done:
            env.abort("internal_error")
        return snapshot()
    finally:
        env.close()


def verify(record_path: Path) -> dict:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    env = StreamEnvironment(record["case"], recorded_calls=record["service_evidence"]["calls"])
    try:
        if record["initial_observation"] != env.observation() or record["contract"] != env.contract():
            raise ValueError("Initial public state changed")
        for event in record["events"]:
            if env.step(event["action"]) != event["observation"]:
                raise ValueError("Action/result replay differs")
        if not env.done:
            env.abort(record["grade"]["termination"])
        if env.grade() != record["grade"] or env.evidence() != record["service_evidence"]:
            raise ValueError("Business grade or executed evidence differs")
        return env.grade()
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--plan", required=True, type=Path)
    command.add_argument("--model", required=True)
    command.add_argument("--out", required=True, type=Path)
    command.add_argument("--runtime-config", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(args.record), ensure_ascii=False))
        return
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    result = run(args.plan, args.model, args.out)
    print(json.dumps({"model": args.model, "grade": result["grade"], "error": result["error"],
                      "usage": result["usage"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
