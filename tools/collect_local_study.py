"""Freeze/collect a declared suite using existing local authorized routes.

No credential values or provider bodies are written to evidence. Historical
study launchers stay byte-pinned; new studies can reuse this entry point.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import time
import tomllib

from pomdp_bench import __version__
from pomdp_bench.collection import prepare_suite, read_run, resume_suite
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "collect"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--suite", type=Path)
    args = parser.parse_args()
    plan = read_json(args.plan)
    if plan["framework_version"] != __version__:
        raise ValueError("Use the declared framework version")
    if args.mode == "prepare":
        if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
            raise ValueError("Commit the complete implementation and plan before preparing")
        if args.suite is None:
            raise ValueError("Preparation requires --suite")
        data = read_json(args.suite)
        if data["generator_version"] != plan["generator_version"] or digest(data) != plan["suite_sha256"]:
            raise ValueError("Suite differs from the preregistered plan")
        count = len(data["cases"]) * len(plan["agents"]) * len(plan["conditions"]) * plan["replicates"]
        if count != plan["expected_episodes"]:
            raise ValueError("Plan matrix count differs")
        manifest = prepare_suite(data, plan["agents"], plan["conditions"], plan["replicates"], args.output, plan["wall_seconds"])
        write_json(args.output / "private/plan-binding.json", {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}, replace=False)
        print(f"Prepared {count} complete episodes; no model called.")
        return
    manifest, _ = read_run(args.output, partial=True)
    if read_json(args.output / "private/plan-binding.json") != {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}:
        raise ValueError("Prepared plan/manifest changed")
    codex = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config_path, auth_path = codex / "config.toml", codex / "auth.json"
    router = codex / "codex-router"
    protected = (config_path, auth_path, router / "native-session-consent.json")
    before = [p.read_bytes() if p.exists() else None for p in protected]
    base = tomllib.loads(config_path.read_text(encoding="utf-8"))["model_providers"]["codex-router"]["base_url"].rstrip("/")
    if base != plan["transport"]["base_url"]:
        raise ValueError("Unexpected route")
    auth = read_json(auth_path)["tokens"]
    token = auth["access_token"]
    part = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    if claims["exp"] <= time.time() + plan["wall_seconds"] * plan["expected_episodes"]:
        raise ValueError("Existing login does not cover planned episodes")
    os.environ["DIRECT_ENDPOINT"] = base + "/responses"
    os.environ["NATIVE_KEY"] = token
    os.environ["NATIVE_HEADERS"] = json.dumps({**plan["transport"]["headers"], "ChatGPT-Account-Id": auth["account_id"]})
    if any(a["api_key_env"] == "ROUTER_KEY" for a in plan["agents"]):
        os.environ["ROUTER_KEY"] = (router / "caller-secret").read_text().strip()
        os.environ["ROUTER_HEADERS"] = json.dumps(plan["transport"]["headers"])
    try:
        report = resume_suite(args.output)
    finally:
        after = [p.read_bytes() if p.exists() else None for p in protected]
        write_json(args.output / "private/settings-check.json", {
            "settings_and_auth_bytes_unchanged": before == after,
            "files": [{"name": p.name, "bytes_unchanged": old == new} for p, old, new in zip(protected, before, after)]})
    print(json.dumps({"episodes": report["episodes"], "complete": report["complete"]}))


if __name__ == "__main__":
    main()
