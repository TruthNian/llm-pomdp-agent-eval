"""Export and independently check all three frozen Astra attempts."""
from __future__ import annotations

import hashlib
import gzip
import json
import os
from pathlib import Path
import runpy
import sys
import tomllib


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
RUN = REPO / "artifacts" / "astra-efforts-v1"
sys.path.insert(0, str(REPO))

from pomdp_bench.collection import read_run, source_hashes  # noqa: E402
from pomdp_bench.evaluation import replay  # noqa: E402
from pomdp_bench.generator import digest  # noqa: E402
from pomdp_bench.stream import suite  # noqa: E402


render = runpy.run_path(str(ROOT.parent / "stream-recovery-v1" / "verify.py"))["render"]
verify_requests = runpy.run_path(str(ROOT.parent / "stream-recovery-continuous-v1" / "verify.py"))["verify_requests"]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha256(raw if path.suffix == ".gz" else raw.replace(b"\r\n", b"\n")).hexdigest()


def read_compressed(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def check(data: dict) -> None:
    plan = read(ROOT / "plan.json")
    names = {agent["name"] for agent in plan["agents"]}
    public_generator_output = suite()
    case = public_generator_output["cases"][0]
    if (data["working_tree_dirty"] or data["expected"] != 3 or data["retained"] != 3
            or len(data["records"]) != 3 or data["case_sha256"] != digest(case)
            or {record["agent"]["name"] for record in data["records"]} != names):
        raise ValueError("Astra matrix incomplete or source tree dirty at preparation")
    if digest(public_generator_output) != plan["suite_sha256"]:
        raise ValueError("Incident suite changed")
    if any(data["source_sha256"].get(path) != value
           for path, value in plan["environment_source_sha256"].items()):
        raise ValueError("Environment source changed")
    settings = data["settings_check"]
    files = {item["name"]: item["bytes_unchanged"] for item in settings["files"]}
    if (set(files) != {"config.toml", "auth.json", "native-session-consent.json"}
            or settings["settings_and_auth_bytes_unchanged"] != all(files.values())
            or not files["auth.json"] or not files["native-session-consent.json"]
            or data["route_base_url_after_collection"] != plan["transport"]["base_url"]):
        raise ValueError("Authentication or observed route evidence changed")
    for record in data["records"]:
        if (record["agent"] not in plan["agents"] or record["framework_version"] != plan["framework_version"]
                or record["condition"] != "open" or record["replicate"] != 0):
            raise ValueError("Attempt differs from frozen plan")
        replay(record, case)
        verify_requests(record)
        for call in record["service_evidence"]["calls"]:
            audit = call["response"].get("audit")
            if audit and (audit["image"] != plan["runtime"]["image"]
                          or audit["components"] != plan["runtime"]["components"]):
                raise ValueError("Runtime differs from frozen image")


def export() -> None:
    target = ROOT / "model-evidence.json.gz"
    if target.exists():
        raise ValueError("Published evidence already exists")
    manifest, records = read_run(RUN)
    if manifest["source_sha256"] != source_hashes():
        raise ValueError("Collector source changed")
    binding = read(RUN / "private" / "plan-binding.json")
    if binding != {"plan_sha256": digest(read(ROOT / "plan.json")),
                   "manifest_sha256": digest(manifest)}:
        raise ValueError("Prepared plan/manifest binding changed")
    data = {key: manifest[key] for key in ("git_revision", "working_tree_dirty", "source_sha256")}
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = tomllib.loads((codex_home / "config.toml").read_text(encoding="utf-8"))
    route = config["model_providers"]["codex-router"]["base_url"].rstrip("/")
    data.update(expected=manifest["expected_episodes"], retained=len(records), records=records,
                case_sha256=digest(manifest["cases"][0]),
                route_base_url_after_collection=route,
                settings_check=read(RUN / "private" / "settings-check.json"))
    check(data)
    target.write_bytes(gzip.compress((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), mtime=0))
    (ROOT / "trajectories.html.gz").write_bytes(gzip.compress(render(data).encode("utf-8"), mtime=0))
    print("Exported three Astra attempts")


def seal() -> None:
    target = ROOT / "execution.json"
    if target.exists():
        raise ValueError("Published seal already exists")
    files = ("plan.json", "README.md", "evidence.py", "model-evidence.json.gz", "trajectories.html.gz",
             "../stream-recovery-v1/verify.py", "../stream-recovery-continuous-v1/verify.py")
    data = read_compressed(ROOT / "model-evidence.json.gz")
    check(data)
    target.write_text(json.dumps({"source_commit": data["git_revision"], "expected_episodes": 3,
                                  "retained_episodes": 3, "file_sha256": {name: sha256(ROOT / name) for name in files}},
                                 indent=2) + "\n", encoding="utf-8", newline="\n")


def verify() -> None:
    execution = read(ROOT / "execution.json")
    if execution["expected_episodes"] != 3 or execution["retained_episodes"] != 3:
        raise ValueError("Incomplete evidence seal")
    for name, expected in execution["file_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError("Published file changed: " + name)
    data = read_compressed(ROOT / "model-evidence.json.gz")
    if execution["source_commit"] != data["git_revision"]:
        raise ValueError("Collector revision changed")
    check(data)
    if gzip.decompress((ROOT / "trajectories.html.gz").read_bytes()).decode("utf-8") != render(data):
        raise ValueError("Readable trajectory differs from evidence")
    print("Verified three retained Astra attempts, request projections, runtime, and business replay")


if __name__ == "__main__":
    {"export": export, "seal": seal, "verify": verify}[sys.argv[1]]()
