"""Publish and replay every frozen Boyue frontier attempt without provider bodies."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))

from pomdp_bench.generator import digest  # noqa: E402
from pomdp_bench.stream import suite  # noqa: E402
from tools.boyue_chat_stream import verify as replay  # noqa: E402


SPECS = (
    ("chat-kimi", "stream-recovery-boyue-frontier-v1", "boyue-frontier-v1-kimi-k3", "kimi-k3"),
    ("chat-deepseek", "stream-recovery-boyue-frontier-v1", "boyue-frontier-v1-deepseek-v4-pro", "deepseek-v4-pro"),
    ("chat-minimax", "stream-recovery-boyue-frontier-v1", "boyue-frontier-v1-minimax-m3", "MiniMax-M3"),
    ("sse-kimi", "stream-recovery-boyue-frontier-sse-v1", "boyue-sse-v1-kimi-k3", "kimi-k3"),
    ("sse-deepseek", "stream-recovery-boyue-frontier-sse-v1", "boyue-sse-v1-deepseek-v4-pro", "deepseek-v4-pro"),
    ("sse-minimax", "stream-recovery-boyue-frontier-sse-v1", "boyue-sse-v1-minimax-m3", "MiniMax-M3"),
    ("sse-qwen-medium", "stream-recovery-boyue-qwen38max-sse-v1", "boyue-qwen38max-sse-v1", "qwen3.8-max"),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def plan_hashes(path: Path) -> set[str]:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return {sha256(raw), sha256(raw.replace(b"\n", b"\r\n"))}


def check_record(label: str, plan_name: str, model: str, record: dict) -> None:
    plan_path = REPO / "studies" / plan_name / "plan.json"
    plan = read(plan_path)
    if (record["study_id"] != plan["study_id"] or record["model"] != model
            or model not in plan["models"] or record["interface"] != "boyue-chat-tools/1"
            or record["plan_sha256"] not in plan_hashes(plan_path)
            or plan["suite_sha256"] != digest(suite())
            or record["grade"]["termination"] != "adapter_error"):
        raise ValueError("Frozen Boyue record mismatch: " + label)
    for relative, expected in plan["source_sha256"].items():
        if sha256((REPO / relative).read_bytes()) != expected:
            raise ValueError("Frozen source changed: " + relative)
    reconstructed = {**record, "case": suite()["cases"][0]}
    if reconstructed["grade"] != replay_record(reconstructed):
        raise ValueError("Business replay differs: " + label)


def replay_record(record: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="boyue-replay-") as temporary:
        path = Path(temporary) / "record.json"
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return replay(path)


def export() -> None:
    compressed_path = ROOT / "trace.json.gz"
    receipt_path = ROOT / "receipt.json"
    if compressed_path.exists() or receipt_path.exists():
        raise ValueError("Published evidence already exists")
    items, receipts = [], []
    for label, plan_name, artifact_name, model in SPECS:
        path = REPO / "artifacts" / artifact_name / "checkpoint.json"
        raw = path.read_bytes()
        original = json.loads(raw)
        if original["case"] != suite()["cases"][0]:
            raise ValueError("Private case differs: " + label)
        record = {key: value for key, value in original.items() if key != "case"}
        check_record(label, plan_name, model, record)
        items.append({"label": label, "plan": plan_name, "record": record})
        receipts.append({"label": label, "private_checkpoint_sha256": sha256(raw),
                         "model": model, "actions": len(record["events"]),
                         "termination": record["grade"]["termination"], "error": record["error"],
                         "elapsed_seconds": record["elapsed_seconds"]})
    trace = json.dumps({"schema": 1, "items": items}, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(trace, mtime=0)
    compressed_path.write_bytes(compressed)
    receipt_path.write_text(json.dumps({"expected": len(SPECS), "retained": len(items),
                                        "suite_sha256": digest(suite()),
                                        "trace_json_sha256": sha256(trace),
                                        "trace_gzip_sha256": sha256(compressed),
                                        "attempts": receipts}, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    print("Exported seven frozen Boyue attempts")


def verify() -> None:
    receipt = read(ROOT / "receipt.json")
    compressed = (ROOT / "trace.json.gz").read_bytes()
    trace = gzip.decompress(compressed)
    if (receipt["expected"] != len(SPECS) or receipt["retained"] != len(SPECS)
            or receipt["suite_sha256"] != digest(suite())
            or receipt["trace_json_sha256"] != sha256(trace)
            or receipt["trace_gzip_sha256"] != sha256(compressed)):
        raise ValueError("Trace seal or retention differs")
    data = json.loads(trace)
    if data["schema"] != 1 or len(data["items"]) != len(SPECS):
        raise ValueError("Unexpected trace structure")
    for spec, item, observed in zip(SPECS, data["items"], receipt["attempts"]):
        label, plan_name, _, model = spec
        if (item["label"] != label or item["plan"] != plan_name
                or observed["label"] != label or observed["model"] != model):
            raise ValueError("Attempt order changed")
        record = item["record"]
        if ("case" in record or len(record["events"]) != observed["actions"]
                or record["grade"]["termination"] != observed["termination"]
                or record["error"] != observed["error"]
                or record["elapsed_seconds"] != observed["elapsed_seconds"]):
            raise ValueError("Published attempt differs")
        check_record(label, plan_name, model, record)
    print("Verified seven retained attempts, frozen plans and offline business replay")


if __name__ == "__main__":
    {"export": export, "verify": verify}[sys.argv[1]]()
