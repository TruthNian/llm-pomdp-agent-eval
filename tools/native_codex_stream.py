"""One-turn Codex runtime pilot against the existing stream incident.

This is an integration pilot, not a replacement for the versioned HTTP agent
adapters or a model-only comparison. Codex owns the dialogue and calls only two
client tools; the evaluator owns the container, public observations and grade.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tomllib

from pomdp_bench.stream import StreamEnvironment, make_case
from pomdp_bench.stream_runtime import configuration


MODEL = "custom/z-ai/glm-5.3"
PROVIDER = "codex-router"
DISABLED = (
    "plugins", "apps", "multi_agent", "multi_agent_v2", "shell_tool",
    "unified_exec", "computer_use", "browser_use", "browser_use_external",
    "in_app_browser", "view_image", "code_mode", "code_mode_host",
    "goals", "sleep_tool", "hooks", "workspace_dependencies",
    "skill_search", "memories", "unbounded_connection_retries",
    "tool_suggest", "image_generation",
)
TOOLS = [
    {"type": "function", "name": "exec",
     "description": "Execute a Bash script in the isolated operations environment.",
     "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}},
                     "required": ["target"], "additionalProperties": False}},
    {"type": "function", "name": "finish", "description": "Hand over the service and end the incident interaction.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
]
ALLOWED_ITEMS = {"userMessage", "reasoning", "agentMessage", "dynamicToolCall"}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def save(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class AppServer:
    def __init__(self, source_home: Path, *, effort: str):
        if effort not in {"low", "high", "max"}:
            raise ValueError("This GLM route supports low/high/max reasoning")
        self.temporary = tempfile.TemporaryDirectory(prefix="pomdp-native-")
        home = Path(self.temporary.name)
        workspace = home / "workspace"
        workspace.mkdir()
        config = tomllib.loads((source_home / "config.toml").read_text(encoding="utf-8"))
        provider = config["model_providers"][PROVIDER]
        if not str(provider["base_url"]).startswith("http://127.0.0.1:"):
            raise ValueError("Expected the explicitly configured loopback router")
        (home / "config.toml").write_text(
            f"[model_providers.{PROVIDER}]\n" +
            "".join(f"{key} = {json.dumps(value)}\n" for key, value in provider.items()), encoding="utf-8")
        # A same-volume hard link avoids copying credentials into a study artifact.
        # The temporary home and link are deleted when the process closes.
        os.link(source_home / "auth.json", home / "auth.json")
        command = [shutil.which("codex") or "codex", "app-server", "--stdio"]
        for flag in DISABLED:
            command += ["--disable", flag]
        for key, value in {
            "web_search": "disabled", "tools.view_image": False,
            "project_doc_max_bytes": 0, "model_reasoning_effort": effort,
            "model_reasoning_summary": "none",
        }.items():
            command += ["-c", key + "=" + json.dumps(value)]
        child_env = os.environ.copy()
        child_env["CODEX_HOME"] = str(home)
        self.process = subprocess.Popen(
            command, cwd=workspace, env=child_env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.messages: queue.Queue[dict] = queue.Queue()
        self.backlog: list[dict] = []
        self.write_lock = threading.Lock()
        self.counter = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        for line in self.process.stdout:
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                continue

    def send(self, value: dict) -> None:
        with self.write_lock:
            self.process.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
            self.process.stdin.flush()

    def next(self, timeout: float) -> dict | None:
        if self.backlog:
            return self.backlog.pop(0)
        try:
            return self.messages.get(timeout=max(0.01, timeout))
        except queue.Empty:
            if self.process.poll() is not None:
                raise RuntimeError("Codex app server exited")
            return None

    def rpc(self, method: str, params: dict, *, timeout: float = 30) -> dict:
        self.counter += 1
        ident = self.counter
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        deferred, self.backlog = self.backlog, []
        try:
            while time.monotonic() < deadline:
                try:
                    message = self.messages.get(timeout=min(1, deadline - time.monotonic()))
                except queue.Empty:
                    if self.process.poll() is not None:
                        raise RuntimeError("Codex app server exited")
                    continue
                if message.get("id") == ident and "method" not in message:
                    if "error" in message:
                        raise RuntimeError(f"Codex RPC {method} rejected: {message['error'].get('code')}")
                    return message["result"]
                deferred.append(message)
            raise TimeoutError(f"Codex RPC {method} deadline exceeded")
        finally:
            self.backlog = deferred + self.backlog

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=8)
        self.temporary.cleanup()


def action(tool: str, arguments) -> dict:
    if tool == "exec" and isinstance(arguments, dict) and set(arguments) == {"target"}:
        return {"command": "exec", "target": arguments["target"]}
    if tool == "finish" and arguments == {}:
        return {"command": "finish"}
    return {"command": "invalid"}


def tool_output(observation: dict) -> dict:
    return {"contentItems": [{"type": "inputText", "text": json.dumps(observation, ensure_ascii=False)}],
            "success": True}


def verify(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
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


def run(out: Path, *, effort: str, wall_seconds: int, idle_seconds: int) -> dict:
    if out.exists():
        raise FileExistsError(f"Attempt directory already exists: {out}")
    out.mkdir(parents=True)
    runtime = configuration()
    if runtime["image"] != "sha256:9ae11d63ae5f3525160b23746fca3f080c976dd9e90956a4f16b12361c33862d":
        raise ValueError("Pilot is frozen to the existing stream image")
    case = make_case()
    env = StreamEnvironment(case)
    initial_observation = env.observation()
    app = None
    started = time.monotonic()
    error = None
    session = None
    usage = None
    tool_calls = 0
    post_handover = False
    turn_status = None
    turn_error = None
    phase = "environment_start"
    checkpoints = out / "checkpoint.json"

    def snapshot():
        record = {
            "pilot_version": "codex-native-stream/1",
            "model": MODEL, "provider": PROVIDER, "effort": effort,
            "runtime_image": runtime["image"], "disabled_host_features": list(DISABLED),
            "dynamic_tools": copy.deepcopy(TOOLS), "session": copy.deepcopy(session),
            "case": case, "contract": env.contract(),
            "initial_observation": initial_observation,
            "events": copy.deepcopy(env.history), "service_evidence": env.evidence(),
            "grade": env.grade(), "usage": copy.deepcopy(usage), "tool_calls": tool_calls,
            "turn_status": turn_status, "post_handover": post_handover,
            "turn_error": copy.deepcopy(turn_error), "phase": phase,
            "error": error, "elapsed_seconds": round(time.monotonic() - started, 6),
        }
        save(checkpoints, record)
        return record

    try:
        snapshot()
        env.start()
        phase = "runtime_start"
        app = AppServer(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")), effort=effort)
        app.rpc("initialize", {"clientInfo": {"name": "pomdp-native-stream", "version": "1.0"},
                               "capabilities": {"experimentalApi": True}})
        app.send({"method": "initialized", "params": {}})
        result = app.rpc("thread/start", {
            "model": MODEL, "modelProvider": PROVIDER, "allowProviderModelFallback": False,
            "ephemeral": True, "cwd": str(Path(app.temporary.name) / "workspace"),
            "environments": [], "runtimeWorkspaceRoots": [], "selectedCapabilityRoots": [],
            "dynamicTools": TOOLS, "approvalPolicy": "never",
            "config": {"model_reasoning_effort": effort, "project_doc_max_bytes": 0},
        })
        if (result.get("model"), result.get("modelProvider"), result.get("reasoningEffort")) != (MODEL, PROVIDER, effort):
            raise RuntimeError("Codex changed model/provider/effort")
        if result.get("instructionSources") != []:
            raise RuntimeError("Unexpected instruction source entered isolated episode")
        tid = result["thread"]["id"]
        session = {"model": result["model"], "provider": result["modelProvider"],
                   "effort": result["reasoningEffort"], "instruction_sources": [],
                   "environment_count": 0, "fallback_allowed": False}
        contract = env.contract()
        prompt = "\n".join((env.initial_alert, contract["task"], contract["workspace"], contract["limits"]))
        phase = "agent_turn"
        turn = app.rpc("turn/start", {"threadId": tid, "environments": [], "effort": effort,
                                      "input": [{"type": "text", "text": prompt, "text_elements": []}]})
        turn_id = turn["turn"]["id"]
        last_progress = time.monotonic()
        while not env.done:
            now = time.monotonic()
            if now - started >= wall_seconds:
                error = "Episode wall deadline exceeded"
                env.abort("wall_limit")
                break
            if now - last_progress >= idle_seconds:
                error = "Codex runtime idle deadline exceeded"
                env.abort("adapter_error")
                break
            message = app.next(min(1, wall_seconds - (now - started), idle_seconds - (now - last_progress)))
            if message is None:
                continue
            method = message.get("method")
            params = message.get("params", {})
            if "id" in message and method:
                if method != "item/tool/call" or params.get("threadId") != tid or params.get("turnId") != turn_id:
                    app.send({"id": message["id"], "error": {"code": -32601, "message": "Unavailable"}})
                    error = "Unexpected client tool request"
                    env.abort("adapter_error")
                    break
                name, arguments = params.get("tool"), params.get("arguments")
                if name not in {"exec", "finish"} or params.get("namespace") not in (None, ""):
                    app.send({"id": message["id"], "error": {"code": -32601, "message": "Unavailable"}})
                    error = "Undeclared tool request"
                    env.abort("adapter_error")
                    break
                tool_calls += 1
                observation = env.step(action(name, arguments))
                snapshot()
                app.send({"id": message["id"], "result": tool_output(observation)})
                last_progress = time.monotonic()
                print(json.dumps({"step": len(env.history), "tool": name,
                                  "done": env.done, "elapsed_seconds": round(last_progress-started, 1)}), flush=True)
            elif method == "item/completed" and params.get("threadId") == tid:
                item_type = params.get("item", {}).get("type")
                if item_type not in ALLOWED_ITEMS:
                    error = f"Unexpected runtime item: {item_type}"
                    env.abort("adapter_error")
                    break
            elif method == "thread/tokenUsage/updated" and params.get("threadId") == tid:
                total = params.get("tokenUsage", {}).get("total", {})
                if all(type(total.get(key)) is int for key in ("inputTokens", "outputTokens")):
                    usage = {"input_tokens": total["inputTokens"], "output_tokens": total["outputTokens"],
                             "reasoning_tokens": total.get("reasoningOutputTokens") if type(total.get("reasoningOutputTokens")) is int else None}
            elif method == "turn/completed" and params.get("threadId") == tid:
                turn_status = params["turn"].get("status")
                if turn_status == "completed":
                    error = "Agent ended its turn without handing over"
                    env.abort("agent_stopped")
                else:
                    detail = params["turn"].get("error") or {}
                    message_text = str(detail.get("message") or "")
                    status = re.search(r"\b([45][0-9]{2})\b", message_text)
                    turn_error = {"code": detail.get("codexErrorInfo"),
                                  "http_status": int(status.group(1)) if status else None,
                                  "message_sha256": sha256(message_text.encode()) if message_text else None}
                    error = "Codex turn failed: " + str(detail.get("codexErrorInfo") or turn_status)
                    env.abort("adapter_error")
                break
        if env.done and env.reason == "finished":
            # The terminal tool call itself is the handover. A final assistant
            # message after it cannot alter the audited business state.
            post_handover = True
        return snapshot()
    except Exception as exc:
        error = f"Local integration failure at {phase}: {type(exc).__name__}"
        if env.runtime is not None and not env.done:
            env.abort("internal_error")
        return snapshot()
    finally:
        if app is not None:
            app.close()
        env.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("run")
    cmd.add_argument("--out", required=True, type=Path)
    cmd.add_argument("--runtime-config", required=True, type=Path)
    cmd.add_argument("--effort", choices=("low", "high", "max"), default="high")
    cmd.add_argument("--wall-seconds", type=int, default=10800)
    cmd.add_argument("--idle-seconds", type=int, default=600)
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(args.record), ensure_ascii=False, indent=2))
        return
    if args.wall_seconds <= 0 or args.idle_seconds <= 0:
        parser.error("Deadlines must be positive")
    os.environ["POMDP_STREAM_CONFIG"] = str(args.runtime_config.resolve())
    record = run(args.out, effort=args.effort,
                 wall_seconds=args.wall_seconds, idle_seconds=args.idle_seconds)
    print(json.dumps({"grade": record["grade"], "error": record["error"],
                      "usage": record["usage"], "tool_calls": record["tool_calls"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
