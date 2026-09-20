"""Three pinned, independently sourced compatibility defects; no plugin registry."""
import hashlib
import json
from pathlib import Path

from .generator import digest
from .repair_runtime import validate_image

VERSION = "repository-repair/2"
TASKS = ("werkzeug_routing", "attrs_preinit", "urllib3_read")
ROOT = Path(__file__).with_name("repair_data")
DESCRIPTIONS = {
    "werkzeug_routing": (
        "pallets/werkzeug",
        "Fix merge_slashes semantics. Setting Map.merge_slashes after construction must affect matching. "
        "With merging disabled globally or on a Rule, repeated slashes must not redirect to that rule. "
        "Preserve ordinary matches, enabled canonical redirects, literal repeated-slash rules, "
        "path/int converters, strict trailing-slash behavior, and method rejection."),
    "attrs_preinit": (
        "python-attrs/attrs",
        "Fix attrs-generated __init__ passing default expressions instead of supplied values to "
        "__attrs_pre_init__. Forward supplied positional/default/factory/keyword-only values correctly. "
        "Preserve omitted defaults, factory NOTHING before initialization, aliases, converters, "
        "slots/frozen classes, self-only hooks and classes without a hook. Factories must run once."),
    "urllib3_read": (
        "urllib3/urllib3",
        "Fix HTTPResponse losing buffered decoded bytes when read(amt) is followed by read() or read(None). "
        "The reported consequence is truncated response content. Preserve byte order without duplication, "
        "repeated partial reads, complete reads, EOF, caching of the remaining body, uncompressed/raw reads, "
        "and gzip/deflate/Brotli decoding. Use real decoder behavior; do not special-case fixture values."),
}


def make_case(image, task):
    validate_image(image)
    if task not in TASKS:
        raise ValueError("Unknown real repair task")
    data = ROOT / task
    files = json.loads((data / "base.json").read_text(encoding="utf-8"))
    provenance = json.loads((data / "provenance.json").read_text(encoding="utf-8"))
    expected = {**provenance["file_sha256"], **provenance.get("generated_file_sha256", {})}
    if {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items()} != expected:
        raise ValueError("Pinned upstream source changed")
    return {"generator_version": VERSION, "family": "repository_repair", "profile": task,
            "domain": "python_repository", "source_task_id": provenance["issue"],
            "base_commit": provenance["base_commit"], "files": files, "image_id": image,
            "check_version": task + ("/2" if task == "urllib3_read" else "/1"),
            "max_steps": 80, "max_checks": 12}


def validate_case(case):
    if digest(case) != digest(make_case(case["image_id"], case["profile"])):
        raise ValueError("Repository portfolio case differs from its pinned contract")


def contract(case):
    repository, task = DESCRIPTIONS[case["profile"]]
    return {"repository": repository + " (complete package source plus selected public docs/tests)",
            "task": task,
            "success": "Deliver a nonempty source patch after all evaluator-owned behavior checks pass "
                       "at the current revision, then finish. Tests/docs cannot change acceptance. "
                       "A reproduction-only pass is insufficient. Every edit expires verification."}
