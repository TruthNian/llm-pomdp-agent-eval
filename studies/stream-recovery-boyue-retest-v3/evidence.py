"""Publish and replay the frozen Boyue repair retests without raw model bodies."""
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
    ("v2-kimi", "stream-recovery-boyue-retest-v2", "boyue-retest-v2-kimi-k3",
     "kimi-k3", "boyue-chat-tools/1"),
    ("v3-kimi", "stream-recovery-boyue-retest-v3", "boyue-retest-v3-kimi-k3",
     "kimi-k3", "boyue-chat-tools/2"),
    ("v3-deepseek", "stream-recovery-boyue-retest-v3", "boyue-retest-v3-deepseek-v4-pro",
     "deepseek-v4-pro", "boyue-chat-tools/2"),
    ("v3-qwen", "stream-recovery-boyue-retest-v3", "boyue-retest-v3-qwen38-max",
     "qwen3.8-max", "boyue-chat-tools/2"),
    ("v3-minimax", "stream-recovery-boyue-retest-v3", "boyue-retest-v3-minimax-m3",
     "MiniMax-M3", "boyue-chat-tools/2"),
    ("v3-mimo", "stream-recovery-boyue-retest-v3", "boyue-retest-v3-mimo-v25-pro",
     "mimo-v2.5-pro", "boyue-chat-tools/2"),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def plan_hashes(path: Path) -> set[str]:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return {sha256(raw), sha256(raw.replace(b"\n", b"\r\n"))}


def check_record(spec: tuple[str, str, str, str, str], record: dict) -> None:
    label, plan_name, _, model, interface = spec
    path = REPO / "studies" / plan_name / "plan.json"
    plan = read(path)
    if (record["study_id"] != plan["study_id"] or record["model"] != model
            or model not in plan["models"] or record["interface"] != interface
            or record["plan_sha256"] not in plan_hashes(path)
            or plan["suite_sha256"] != digest(suite())
            or len(record["events"]) > plan["limits"]["max_actions"]):
        raise ValueError("Frozen record mismatch: " + label)
    for relative, expected in plan["source_sha256"].items():
        if sha256((REPO / relative).read_bytes()) != expected:
            raise ValueError("Frozen source changed: " + relative)
    for call in record["service_evidence"]["calls"]:
        audit = call["response"].get("audit")
        if audit and (audit["image"] != plan["runtime"]["image"]
                      or audit["components"] != plan["runtime"]["components"]):
            raise ValueError("Frozen runtime differs: " + label)
    reconstructed = {**record, "case": suite()["cases"][0]}
    with tempfile.TemporaryDirectory(prefix="boyue-retest-replay-") as temporary:
        location = Path(temporary) / "record.json"
        location.write_text(json.dumps(reconstructed, ensure_ascii=False), encoding="utf-8")
        if replay(location) != record["grade"]:
            raise ValueError("Business replay differs: " + label)


def export() -> None:
    trace_path, receipt_path = ROOT / "trace.json.gz", ROOT / "receipt.json"
    if trace_path.exists() or receipt_path.exists():
        raise FileExistsError("Published evidence already exists")
    items, receipts = [], []
    for spec in SPECS:
        label, plan_name, artifact_name, model, _ = spec
        raw = (REPO / "artifacts" / artifact_name / "checkpoint.json").read_bytes()
        original = json.loads(raw)
        if original["case"] != suite()["cases"][0]:
            raise ValueError("Private case changed: " + label)
        record = {key: value for key, value in original.items() if key != "case"}
        check_record(spec, record)
        items.append({"label": label, "plan": plan_name, "record": record})
        grade = record["grade"]
        traffic = record["service_evidence"]["calls"][-1]["response"]["audit"]["traffic"]
        receipts.append({"label": label, "model": model,
                         "private_checkpoint_sha256": sha256(raw),
                         "actions": len(record["events"]),
                         "logical_requests": record["usage"]["requests"],
                         "wire_attempts": sum(len(a.get("wire_attempts", []))
                                              for a in record["request_audit"]),
                         "success": grade["success"], "termination": grade["termination"],
                         "error": record["error"], "elapsed_seconds": record["elapsed_seconds"],
                         "traffic_write_failures": grade["traffic_write_failures"],
                         "traffic_attempts": sum(len(batch["commands"]) for batch in traffic),
                         "final_order_errors": grade["phases"][-1]["order_errors"],
                         "final_missing_bookings": grade["phases"][-1]["missing_bookings"]})
    trace = json.dumps({"schema": 1, "items": items}, ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(trace, mtime=0)
    trace_path.write_bytes(compressed)
    receipt_path.write_text(json.dumps({"expected": len(SPECS), "retained": len(items),
        "suite_sha256": digest(suite()), "trace_json_sha256": sha256(trace),
        "trace_gzip_sha256": sha256(compressed), "attempts": receipts},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Exported six frozen Boyue retest attempts")


def verify() -> None:
    receipt = read(ROOT / "receipt.json")
    compressed = (ROOT / "trace.json.gz").read_bytes()
    trace = gzip.decompress(compressed)
    if (receipt["expected"] != len(SPECS) or receipt["retained"] != len(SPECS)
            or receipt["suite_sha256"] != digest(suite())
            or receipt["trace_json_sha256"] != sha256(trace)
            or receipt["trace_gzip_sha256"] != sha256(compressed)):
        raise ValueError("Trace seal or retention differs")
    items = json.loads(trace)["items"]
    if len(items) != len(SPECS):
        raise ValueError("Wrong number of retained attempts")
    for spec, item, observed in zip(SPECS, items, receipt["attempts"]):
        label, plan_name, _, model, _ = spec
        record = item["record"]
        grade = record["grade"]
        traffic = record["service_evidence"]["calls"][-1]["response"]["audit"]["traffic"]
        if (item["label"] != label or item["plan"] != plan_name or "case" in record
                or observed["label"] != label or observed["model"] != model
                or observed["actions"] != len(record["events"])
                or observed["logical_requests"] != record["usage"]["requests"]
                or observed["wire_attempts"] != sum(len(a.get("wire_attempts", []))
                                                      for a in record["request_audit"])
                or observed["success"] != grade["success"]
                or observed["termination"] != grade["termination"]
                or observed["error"] != record["error"]
                or observed["elapsed_seconds"] != record["elapsed_seconds"]
                or observed["traffic_write_failures"] != grade["traffic_write_failures"]
                or observed["traffic_attempts"] != sum(len(batch["commands"])
                                                        for batch in traffic)
                or observed["final_order_errors"] != grade["phases"][-1]["order_errors"]
                or observed["final_missing_bookings"] != grade["phases"][-1]["missing_bookings"]):
            raise ValueError("Published record differs: " + label)
        check_record(spec, record)
    print("Verified six retained retests, frozen plans and offline business replay")


if __name__ == "__main__":
    {"export": export, "verify": verify}[sys.argv[1]]()
