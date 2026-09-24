"""Frozen Boyue SSE retest route with visible, bounded wire retries.

Keep the original runner byte-for-byte for its earlier study hashes. An HTTP
response is never acted on until it is complete and parsed; retrying before
that boundary cannot duplicate an environment action.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from tools import boyue_chat_stream as core
from tools import boyue_chat_stream_sse_v2 as sse


RETRYABLE_HTTP = {429, 500, 502, 503, 504}


def options_for(plan: dict, model: str) -> dict:
    if plan["transport"]["stream"] is not True or model not in plan["models"]:
        raise ValueError("Model or transport outside the frozen plan")
    options = plan["interface"]["request_options_by_model"][model]
    if (set(options) - {"parallel_tool_calls", "reasoning_effort"}
            or options.get("parallel_tool_calls") is not False
            or ("reasoning_effort" in options and not isinstance(options["reasoning_effort"], str))):
        raise ValueError("Unsupported frozen request options")
    return options


def retryable(exc: Exception, attempt: dict) -> bool:
    return ((isinstance(exc, RuntimeError) and str(exc) in {"transport_error", "timeout"})
            or (isinstance(exc, RuntimeError) and str(exc) == "http_error"
                and attempt.get("http_status") in RETRYABLE_HTTP)
            or (isinstance(exc, ValueError) and str(exc) == "incomplete_sse"))


def exchange(url: str, key: str, payload: dict, audit: dict, *, timeout: float,
             byte_limit: int, options: dict, max_attempts: int) -> dict:
    if max_attempts not in (1, 2):
        raise ValueError("Only one or two frozen wire attempts are supported")
    deadline = time.monotonic() + timeout
    audit["wire_attempts"] = []
    for number in range(max_attempts):
        attempt: dict = {}
        audit["wire_attempts"].append(attempt)
        try:
            response = sse.exchange(url, key, {**payload, **options}, attempt,
                                    timeout=max(0.001, deadline - time.monotonic()),
                                    byte_limit=byte_limit)
            choice = response["choices"][0]
            calls = choice["message"].get("tool_calls") or []
            audit.update(attempt, outcome="response", call_count=len(calls),
                         finish_reason=choice["finish_reason"],
                         tool_names=[call.get("function", {}).get("name") for call in calls])
            return response
        except (RuntimeError, ValueError) as exc:
            attempt["error"] = type(exc).__name__ + ":" + str(exc)
            if number + 1 >= max_attempts or not retryable(exc, attempt):
                audit.update(attempt)
                raise
            pause = min(1.0, max(0.0, deadline - time.monotonic()))
            if pause:
                time.sleep(pause)
    raise AssertionError("unreachable")


def run(plan_path: Path, model: str, output: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    options = options_for(plan, model)
    max_attempts = plan["transport"]["max_wire_attempts_per_turn"]

    def route(url: str, key: str, payload: dict, audit: dict, *, timeout: float,
              byte_limit: int) -> dict:
        if payload.get("model") != model:
            raise ValueError("Requested model changed")
        return exchange(url, key, payload, audit, timeout=timeout,
                        byte_limit=byte_limit, options=options,
                        max_attempts=max_attempts)

    original = core.exchange
    core.exchange = route
    try:
        return core.run(plan_path, model, output)
    finally:
        core.exchange = original


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
