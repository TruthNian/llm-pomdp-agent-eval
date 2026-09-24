"""Run a frozen Boyue SSE study with ordinary Chat request options."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tools import boyue_chat_stream as core
from tools import boyue_chat_stream_sse as sse


def request_options(plan: dict, model: str) -> dict:
    if (plan["models"] != [model] or plan["transport"]["stream"] is not True
            or plan["interface"]["kind"] != "boyue-chat-tools/1"):
        raise ValueError("Model or SSE interface differs from the frozen plan")
    options = plan["interface"].get("request_options", {})
    if not isinstance(options, dict) or set(options) - {"parallel_tool_calls", "reasoning_effort"}:
        raise ValueError("Unsupported Chat request option")
    if "parallel_tool_calls" in options and type(options["parallel_tool_calls"]) is not bool:
        raise ValueError("parallel_tool_calls must be boolean")
    if "reasoning_effort" in options and not isinstance(options["reasoning_effort"], str):
        raise ValueError("reasoning_effort must be a string")
    return options


def run(plan_path: Path, model: str, output: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    options = request_options(plan, model)

    def exchange(url: str, key: str, payload: dict, audit: dict, *, timeout: float, byte_limit: int) -> dict:
        if payload.get("model") != model:
            raise ValueError("Requested model changed")
        return sse.exchange(url, key, {**payload, **options}, audit,
                            timeout=timeout, byte_limit=byte_limit)

    original = core.exchange
    core.exchange = exchange
    try:
        return core.run(plan_path, model, output)
    finally:
        core.exchange = original


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--plan", type=Path, required=True)
    command.add_argument("--model", required=True)
    command.add_argument("--out", type=Path, required=True)
    command.add_argument("--runtime-config", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(core.verify(args.record), ensure_ascii=False))
        return
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    result = run(args.plan, args.model, args.out)
    print(json.dumps({"model": args.model, "grade": result["grade"], "error": result["error"],
                      "usage": result["usage"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
