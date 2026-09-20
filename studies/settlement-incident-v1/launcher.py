"""Use the existing authorized local routes; keep every episode and request."""
import base64
import json
import os
from pathlib import Path
import sys
import time
import tomllib

from pomdp_bench import __version__
from pomdp_bench.collection import prepare_suite, read_run, resume_suite
from pomdp_bench.generator import digest
from pomdp_bench.incident import suite
from pomdp_bench.storage import read_json, write_json


def main():
    mode, output = sys.argv[1], Path(sys.argv[2])
    plan = read_json(Path(__file__).with_name("plan.json"))
    if plan["framework_version"] != __version__:
        raise ValueError("Use the frozen source version")
    if mode == "prepare":
        manifest = prepare_suite(suite(), plan["agents"], plan["conditions"], 1, output, plan["wall_seconds"])
        if manifest["working_tree_dirty"] or manifest["expected_episodes"] != 2:
            raise ValueError("Commit the complete implementation before preparing collection")
        write_json(output / "private/plan-binding.json", {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}, replace=False)
        print("Prepared two full interactive episodes; no model called.")
        return
    if mode != "collect":
        raise ValueError("Use prepare or collect")
    manifest, _ = read_run(output, partial=True)
    if read_json(output / "private/plan-binding.json") != {"plan_sha256": digest(plan), "manifest_sha256": digest(manifest)}:
        raise ValueError("Plan changed after preparation")
    codex_path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config_path, auth_path = codex_path / "config.toml", codex_path / "auth.json"
    router_path = codex_path / "codex-router"
    protected = (config_path, auth_path, router_path / "native-session-consent.json")
    before = [p.read_bytes() if p.exists() else None for p in protected]
    base = tomllib.loads(config_path.read_text(encoding="utf-8"))["model_providers"]["codex-router"]["base_url"].rstrip("/")
    if base != plan["transport"]["base_url"]:
        raise ValueError("Unexpected local route")
    auth = read_json(auth_path)["tokens"]
    token = auth["access_token"]
    middle = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(middle + "=" * (-len(middle) % 4)))
    if claims["exp"] <= time.time() + plan["wall_seconds"] * 2:
        raise ValueError("Existing login does not cover both planned episodes")
    os.environ["DIRECT_ENDPOINT"] = base + "/responses"
    os.environ["NATIVE_KEY"] = token
    os.environ["NATIVE_HEADERS"] = json.dumps({**plan["transport"]["headers"], "ChatGPT-Account-Id": auth["account_id"]})
    os.environ["ROUTER_KEY"] = (router_path / "caller-secret").read_text().strip()
    os.environ["ROUTER_HEADERS"] = json.dumps(plan["transport"]["headers"])
    try:
        report = resume_suite(output)
    finally:
        write_json(output / "private/settings-check.json", {"settings_and_auth_bytes_unchanged": before == [p.read_bytes() if p.exists() else None for p in protected]})
    print(json.dumps({"episodes": report["episodes"], "complete": report["complete"]}))


if __name__ == "__main__":
    main()
