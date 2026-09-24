"""Boyue incident runner that executes every returned tool call in order.

The old one-call runner remains frozen for its published studies. Provider
tool batches are executed sequentially because the environment is stateful.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import time

from pomdp_bench import __version__
from pomdp_bench.generator import digest
from pomdp_bench.model_io import strict_json
from pomdp_bench.stream import StreamEnvironment, suite
from pomdp_bench.stream_runtime import configuration
from tools import boyue_chat_stream as core
from tools import boyue_chat_stream_v2 as wire


def actions_from_response(data: dict, expected_model: str) -> tuple[list[tuple[dict, str]], dict]:
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
        message = copy.deepcopy(message)
        message["content"] = message.get("content") or ""
        return [], message
    if choice.get("finish_reason") != "tool_calls" or not isinstance(calls, list) or not calls:
        raise ValueError("invalid_tool_count_or_finish")
    actions = []
    identifiers: set[str] = set()
    for index, call in enumerate(calls):
        if not isinstance(call, dict) or call.get("type") != "function":
            raise ValueError("invalid_tool_call")
        identifier = call.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError("invalid_tool_call_id")
        identifiers.add(identifier)
        function = call.get("function")
        if not isinstance(function, dict) or function.get("name") not in ("exec", "finish"):
            raise ValueError("undeclared_tool")
        arguments = strict_json(function.get("arguments", ""))
        if function["name"] == "exec" and isinstance(arguments, dict) and set(arguments) == {"target"} and isinstance(arguments["target"], str):
            action = {"command": "exec", "target": arguments["target"]}
        elif function["name"] == "finish" and arguments == {}:
            if index != len(calls) - 1:
                raise ValueError("finish_not_last")
            action = {"command": "finish"}
        else:
            action = {"command": "invalid_model_output"}
        actions.append((action, identifier))
    message = copy.deepcopy(message)
    message["content"] = message.get("content") or ""
    return actions, message


def run(plan_path: Path, model: str, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("One-shot output path already exists")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    options = wire.options_for(plan, model)
    if plan["framework_version"] != __version__ or plan["interface"]["kind"] != "boyue-chat-tools/2":
        raise ValueError("Framework or interface outside the frozen plan")
    root = Path(__file__).resolve().parents[1]
    for relative, expected in plan["source_sha256"].items():
        if core.sha256((root / relative).read_bytes()) != expected:
            raise ValueError("Frozen source changed: " + relative)
    if digest(suite()) != plan["suite_sha256"]:
        raise ValueError("Frozen suite changed")
    runtime = configuration()
    if any(runtime.get(field) != value for field, value in plan["runtime"].items()):
        raise ValueError("Frozen runtime changed")
    base, key = core.registration()
    if base != plan["transport"]["base_url"] or not key:
        raise ValueError("Boyue registration changed")
    output.mkdir(parents=True)
    case = suite()["cases"][0]
    env = StreamEnvironment(case)
    initial, contract = env.observation(), env.contract()
    messages = [{"role": "system", "content": "Follow the task contract. Use the available tools to act."},
                {"role": "user", "content": json.dumps({"protocol_version": 1, "task": contract,
                    "observation": initial, "history": []}, ensure_ascii=False)}]
    usage = {"requests": 0, "reports": 0, "input_tokens": 0, "output_tokens": 0,
             "reasoning_reports": 0, "reasoning_tokens": 0}
    audits = []
    started = time.monotonic()
    error = None
    phase = "environment_start"

    def snapshot() -> dict:
        record = {"study_id": plan["study_id"], "plan_sha256": core.sha256(plan_path.read_bytes()),
                  "model": model, "interface": "boyue-chat-tools/2", "case": case,
                  "contract": contract, "initial_observation": initial,
                  "events": copy.deepcopy(env.history), "service_evidence": env.evidence(),
                  "grade": env.grade(), "usage": copy.deepcopy(usage),
                  "request_audit": copy.deepcopy(audits), "phase": phase, "error": error,
                  "elapsed_seconds": round(time.monotonic() - started, 6)}
        core.save(output / "checkpoint.json", record)
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
            payload = {"model": model, "messages": messages, "tools": core.TOOLS, "stream": False}
            audit = {"outcome": "in_flight"}
            audits.append(audit)
            usage["requests"] += 1
            snapshot()
            try:
                response = wire.exchange(base + "/chat/completions", key, payload, audit,
                    timeout=min(remaining, plan["limits"]["request_seconds"]),
                    byte_limit=plan["limits"]["response_bytes"], options=options,
                    max_attempts=plan["transport"]["max_wire_attempts_per_turn"])
                core.update_usage(usage, response.get("usage"))
                actions, assistant = actions_from_response(response, model)
                audit.update(returned_model=response.get("model"),
                             outcome="action" if actions else "agent_stopped")
            except Exception as exc:
                error = type(exc).__name__ + ":" + (str(exc) if isinstance(exc, (RuntimeError, ValueError)) else "protocol_error")
                audit["outcome"] = error
                env.abort("adapter_error")
                break
            if not actions:
                error = "Agent ended without calling finish"
                env.abort("agent_stopped")
                break
            messages.append(assistant)
            for action, identifier in actions:
                if env.done:
                    break
                observation = env.step(action)
                messages.append({"role": "tool", "tool_call_id": identifier,
                                 "content": json.dumps(observation, ensure_ascii=False, allow_nan=False)})
                snapshot()
                print(json.dumps({"model": model, "step": len(env.history), "tool": action["command"],
                                  "done": env.done, "elapsed_seconds": round(time.monotonic() - started, 1)}),
                      flush=True)
        return snapshot()
    except Exception as exc:
        error = "Local integration failure at " + phase + ":" + type(exc).__name__
        if not env.done:
            env.abort("internal_error")
        return snapshot()
    finally:
        env.close()


def main() -> None:
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
        print(json.dumps(core.verify(args.record), ensure_ascii=False))
        return
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    result = run(args.plan, args.model, args.out)
    print(json.dumps({"model": args.model, "grade": result["grade"],
                      "error": result["error"], "usage": result["usage"]},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
