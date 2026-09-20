"""Explicit installed-route launcher for the authorized, frozen public pilot only."""
import base64
import json
import os
from pathlib import Path
import sys
import time
import tomllib

from pomdp_bench import __version__
from pomdp_bench.collection import prepare_suite, read_run, resume_suite
from pomdp_bench.coverage import VERSION, suite
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json, write_json


def main():
    mode, output = sys.argv[1], Path(sys.argv[2])
    plan = read_json(Path(__file__).with_name("plan.json"))
    if mode not in ("prepare", "collect") or plan["framework_version"] != __version__ or plan["generator_version"] != VERSION:
        raise ValueError("Use the frozen source and prepare/collect mode")
    if mode == "prepare":
        data = suite(plan["development_seeds"], plan["scales"])
        manifest = prepare_suite(data, plan["agents"], plan["conditions"], plan["replicates"], output, plan["wall_seconds"])
        if manifest["expected_episodes"] != plan["expected_episodes"]:
            raise ValueError("Unexpected calibration matrix")
        write_json(output / "private/plan-binding.json", {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}, replace=False)
        print(json.dumps({"prepared": manifest["expected_episodes"], "public_development_seeds": plan["development_seeds"]}))
        return
    manifest, _ = read_run(output, partial=True)
    if read_json(output / "private/plan-binding.json") != {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}:
        raise ValueError("Changed plan or manifest")
    codex_path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config_path, auth_path = codex_path / "config.toml", codex_path / "auth.json"
    router_path = codex_path / "codex-router"
    protected = (config_path, auth_path, router_path / "native-session-consent.json")
    before = [p.read_bytes() if p.exists() else None for p in protected]
    base = tomllib.loads(config_path.read_text(encoding="utf-8"))["model_providers"]["codex-router"]["base_url"].rstrip("/")
    if base != plan["transport"]["base_url"] or base != "http://127.0.0.1:4202/v1":
        raise ValueError("Only the inspected loopback route is authorized by this launcher")
    if [a["model"] for a in plan["agents"]] != ["gpt-5.6-sol", "custom/z-ai/glm-5.3"]:
        raise ValueError("Only the two user-authorized models are configured")
    auth = json.loads(auth_path.read_text(encoding="utf-8"))["tokens"]
    token = auth["access_token"]
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    if claims["exp"] <= time.time() + plan["wall_seconds"] * plan["expected_episodes"]:
        raise ValueError("Refresh the existing Codex login before this fixed pilot")
    os.environ["DIRECT_ENDPOINT"] = base + "/responses"
    os.environ["NATIVE_KEY"] = token
    os.environ["NATIVE_HEADERS"] = json.dumps({**plan["transport"]["headers"], "ChatGPT-Account-Id": auth["account_id"]})
    os.environ["ROUTER_KEY"] = (router_path / "caller-secret").read_text().strip()
    os.environ["ROUTER_HEADERS"] = json.dumps(plan["transport"]["headers"])
    try:
        report = resume_suite(output)
    finally:
        unchanged = [p.read_bytes() if p.exists() else None for p in protected] == before
        write_json(output / "private/settings-check.json", {"settings_and_auth_bytes_unchanged": unchanged})
    print(json.dumps({"complete": report["complete"], "episodes": report["episodes"],
                      "settings_and_auth_bytes_unchanged": unchanged}))


if __name__ == "__main__":
    main()
