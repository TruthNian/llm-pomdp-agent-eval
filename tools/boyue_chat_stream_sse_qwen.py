"""Frozen Qwen3.8 Max SSE follow-up with explicit medium effort."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tools import boyue_chat_stream as core
from tools import boyue_chat_stream_sse as sse


MODEL = "qwen3.8-max"
EFFORT = "medium"


def exchange(url: str, key: str, payload: dict, audit: dict, *, timeout: float, byte_limit: int) -> dict:
    if payload.get("model") != MODEL:
        raise ValueError("Qwen follow-up model changed")
    return sse.exchange(url, key, {**payload, "reasoning_effort": EFFORT}, audit,
                        timeout=timeout, byte_limit=byte_limit)


def run(plan_path: Path, output: Path) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if (plan["models"] != [MODEL] or plan["transport"]["stream"] is not True
            or plan["interface"]["reasoning_effort"] != EFFORT):
        raise ValueError("Qwen follow-up differs from the frozen route")
    original = core.exchange
    core.exchange = exchange
    try:
        return core.run(plan_path, MODEL, output)
    finally:
        core.exchange = original


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--plan", required=True, type=Path)
    command.add_argument("--out", required=True, type=Path)
    command.add_argument("--runtime-config", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(core.verify(args.record), ensure_ascii=False))
        return
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    result = run(args.plan, args.out)
    print(json.dumps({"model": MODEL, "grade": result["grade"], "error": result["error"],
                      "usage": result["usage"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
