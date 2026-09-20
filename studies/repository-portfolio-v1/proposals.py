"""Six immutable single-proposal attempts using the existing HTTP/atomic I/O path."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

from pomdp_bench import __version__
from pomdp_bench.collection import source_hashes
from pomdp_bench.generator import digest
from pomdp_bench.model_io import AdapterError, HttpAgent, request_body
from pomdp_bench.repair import RepairEnvironment, make_case
from pomdp_bench.repair_portfolio import contract
from pomdp_bench.storage import collection_lock, read_json, write_json

HERE = Path(__file__).resolve().parent
PLACEHOLDER_IMAGE = "sha256:" + "0" * 64  # No source execution in this process.


def public_request(plan, task):
    case = make_case(PLACEHOLDER_IMAGE, task)
    return {"protocol_version": 1,
            "task": {**contract(case),
                     "mode": "Single source-patch proposal. No execution or additional tool calls are available in this baseline.",
                     "response": {"command": "submit_patch", "target": [{"path": "src/package/file.py", "old": "unique exact source text", "new": "replacement"}]},
                     "limits": f"At most {plan['max_edits']} sequential edits to supplied source files; each old string must match exactly once. Each old/new string is at most 65536 characters. Return JSON only."},
            "observation": {"files": {p: case["files"][p] for p in plan["context_paths"][task]}},
            "history": []}


def proposal_edits(plan, task, action):
    if (not isinstance(action, dict) or set(action) != {"command", "target"}
            or action["command"] != "submit_patch" or not isinstance(action["target"], list)
            or not 1 <= len(action["target"]) <= plan["max_edits"]):
        raise ValueError("Invalid patch submission schema")
    env = RepairEnvironment(make_case(PLACEHOLDER_IMAGE, task))
    edits = []
    for target in action["target"]:
        if not isinstance(target, dict) or target.get("path") not in plan["context_paths"][task]:
            raise ValueError("Patch targets a file outside the supplied baseline context")
        edit = {"command": "edit", "target": target}
        if env.step(edit)["result"]["kind"] != "edited":
            raise ValueError("Patch edit does not match the exact source or action limits")
        edits.append(edit)
    return edits, env.evidence()["patch"]


def prepare(plan, output):
    if __version__ != plan["framework_version"]:
        raise ValueError("Use the frozen proposal source version")
    if subprocess.check_output(["git", "status", "--porcelain"]).strip():
        raise ValueError("Freeze and commit source before preparing model calls")
    evidence = read_json(HERE / "control-evidence.json")
    if len(evidence["outcomes"]) != 12 or any(
        r["grade"]["success"] != (r["control"] == "upstream-artifact") or r["fresh_recheck_error"] is not None
        for r in evidence["outcomes"]
    ):
        raise ValueError("Real artifact controls have not passed")
    requests = {task: public_request(plan, task) for task in plan["context_paths"]}
    manifest = {"plan": plan, "plan_sha256": digest(plan), "source_sha256": source_hashes(),
                "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
                "public_requests": requests, "expected_attempts": plan["expected_attempts"]}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "private/manifest.json", manifest, replace=False)
    write_json(output / "private/manifest-binding.json", {"sha256": digest(manifest)}, replace=False)
    print(json.dumps({"prepared": 6, "git_revision": manifest["git_revision"]}), flush=True)


def collect(plan, output):
    manifest = read_json(output / "private/manifest.json")
    if (digest(manifest) != read_json(output / "private/manifest-binding.json")["sha256"]
            or digest(plan) != manifest["plan_sha256"] or source_hashes() != manifest["source_sha256"]
            or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest["launcher_sha256"]):
        raise ValueError("Plan or source changed after preparation")
    config = {a["name"]: a for a in plan["agents"]}
    codex = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config_path, auth_path = codex / "config.toml", codex / "auth.json"
    router = codex / "codex-router"
    protected = (config_path, auth_path, router / "native-session-consent.json")
    before = [p.read_bytes() if p.exists() else None for p in protected]
    base = tomllib.loads(config_path.read_text(encoding="utf-8"))["model_providers"]["codex-router"]["base_url"].rstrip("/")
    if base != plan["transport"]["base_url"] or base != "http://127.0.0.1:4202/v1":
        raise ValueError("Unexpected local route")
    auth = read_json(auth_path)["tokens"]
    token = auth["access_token"]
    middle = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(middle + "=" * (-len(middle) % 4)))
    if claims["exp"] <= time.time() + plan["request_seconds"] * plan["expected_attempts"]:
        raise ValueError("Existing login does not cover the planned calls")
    os.environ["DIRECT_ENDPOINT"] = base + "/responses"
    os.environ["NATIVE_KEY"] = token
    os.environ["NATIVE_HEADERS"] = json.dumps({**plan["transport"]["headers"], "ChatGPT-Account-Id": auth["account_id"]})
    os.environ["ROUTER_KEY"] = (router / "caller-secret").read_text().strip()
    os.environ["ROUTER_HEADERS"] = json.dumps(plan["transport"]["headers"])
    try:
        with collection_lock(output):
            for index, (task, name) in enumerate(plan["order"]):
                dest = output / "private" / f"attempt-{index}.json"
                start = output / "private" / f"start-{index}.json"
                if dest.exists():
                    continue
                row = {"index": index, "task": task, "agent": config[name], "action": None,
                       "edits": None, "patch": None, "usage": None, "request_audit": [],
                       "error": None, "elapsed_seconds": None}
                if start.exists():
                    row["error"] = "Interrupted attempt; request outcome and usage unknown; not retried"
                    write_json(dest, row, replace=False)
                    continue
                request = manifest["public_requests"][task]
                body = json.dumps(request_body(config[name], request), ensure_ascii=False, allow_nan=False).encode()
                write_json(start, {"task": task, "agent": name, "plan_sha256": digest(plan),
                                   "request_sha256": hashlib.sha256(body).hexdigest()}, replace=False)
                started, agent = time.monotonic(), None
                try:
                    agent = HttpAgent(config[name])
                    row["action"] = agent.act(request, timeout=plan["request_seconds"])
                    row["edits"], row["patch"] = proposal_edits(plan, task, row["action"])
                except (AdapterError, ValueError) as exc:
                    row["error"] = str(exc)
                except Exception as exc:
                    row["error"] = "Internal proposal error: " + type(exc).__name__
                row["elapsed_seconds"] = round(time.monotonic() - started, 6)
                if agent is not None:
                    row["request_audit"] = agent.request_audit
                    row["partial_usage"] = agent.usage
                    row["usage"] = agent.usage if agent.usage["requests_with_usage"] == 1 else None
                write_json(dest, row, replace=False)
                print(json.dumps({"index": index, "task": task, "agent": name,
                                  "proposal_valid": row["edits"] is not None, "error": row["error"],
                                  "seconds": row["elapsed_seconds"]}), flush=True)
    finally:
        write_json(output / "private/settings-check.json",
                   {"settings_and_auth_bytes_unchanged": before == [p.read_bytes() if p.exists() else None for p in protected]})


if __name__ == "__main__":
    mode, directory = sys.argv[1], Path(sys.argv[2])
    plan = read_json(HERE / "proposal_plan.json")
    if mode == "prepare":
        prepare(plan, directory)
    elif mode == "collect":
        collect(plan, directory)
    else:
        raise ValueError("Use prepare or collect")
