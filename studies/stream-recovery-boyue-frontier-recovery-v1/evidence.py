"""Retain and replay the three preregistered Boyue integration follow-ups."""
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
    ("mimo-serial-sse", "stream-recovery-boyue-mimo25pro-sse-v1", "boyue-mimo25pro-sse-v1", "mimo-v2.5-pro"),
    ("doubao-chat", "stream-recovery-boyue-doubao21pro-chat-v1", "boyue-doubao21pro-chat-v1", "doubao-seed-2-1-pro-260628"),
    ("minimax-serial-sse", "stream-recovery-boyue-minimaxm3-sse-serial-v1", "boyue-minimaxm3-sse-serial-v1", "MiniMax-M3"),
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
            or plan["models"] != [model] or record["interface"] != "boyue-chat-tools/1"
            or record["plan_sha256"] not in plan_hashes(plan_path)
            or plan["suite_sha256"] != digest(suite())
            or len(record["events"]) > plan["limits"]["max_actions"]):
        raise ValueError("Frozen Boyue record mismatch: " + label)
    for relative, expected in plan["source_sha256"].items():
        if sha256((REPO / relative).read_bytes()) != expected:
            raise ValueError("Frozen source changed: " + relative)
    for call in record["service_evidence"]["calls"]:
        audit = call["response"].get("audit")
        if audit and (audit["image"] != plan["runtime"]["image"]
                      or audit["components"] != plan["runtime"]["components"]):
            raise ValueError("Runtime differs from frozen plan")
    reconstructed = {**record, "case": suite()["cases"][0]}
    with tempfile.TemporaryDirectory(prefix="boyue-followup-replay-") as temporary:
        path = Path(temporary) / "record.json"
        path.write_text(json.dumps(reconstructed, ensure_ascii=False), encoding="utf-8")
        if record["grade"] != replay(path):
            raise ValueError("Business replay differs: " + label)


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
        grade = record["grade"]
        traffic = record["service_evidence"]["calls"][-1]["response"]["audit"]["traffic"]
        receipts.append({"label": label, "private_checkpoint_sha256": sha256(raw),
                         "model": model, "actions": len(record["events"]),
                         "requests": record["usage"]["requests"],
                         "success": grade["success"], "termination": grade["termination"],
                         "error": record["error"], "elapsed_seconds": record["elapsed_seconds"],
                         "traffic_write_failures": grade["traffic_write_failures"],
                         "traffic_attempts": sum(len(batch["commands"]) for batch in traffic),
                         "final_order_errors": grade["phases"][-1]["order_errors"],
                         "final_missing_bookings": grade["phases"][-1]["missing_bookings"]})
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
    print("Exported three frozen Boyue follow-ups")


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
        record = item["record"]
        grade = record["grade"]
        traffic = record["service_evidence"]["calls"][-1]["response"]["audit"]["traffic"]
        if (item["label"] != label or item["plan"] != plan_name
                or observed["label"] != label or observed["model"] != model
                or "case" in record or len(record["events"]) != observed["actions"]
                or record["usage"]["requests"] != observed["requests"]
                or grade["success"] != observed["success"]
                or grade["termination"] != observed["termination"]
                or record["error"] != observed["error"]
                or record["elapsed_seconds"] != observed["elapsed_seconds"]
                or grade["traffic_write_failures"] != observed["traffic_write_failures"]
                or sum(len(batch["commands"]) for batch in traffic) != observed["traffic_attempts"]
                or grade["phases"][-1]["order_errors"] != observed["final_order_errors"]
                or grade["phases"][-1]["missing_bookings"] != observed["final_missing_bookings"]):
            raise ValueError("Published attempt differs")
        check_record(label, plan_name, model, record)
    print("Verified three retained Boyue follow-ups, frozen plans and offline business replay")


if __name__ == "__main__":
    {"export": export, "verify": verify}[sys.argv[1]]()
