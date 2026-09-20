"""Repository repair: inspect real source, edit it, verify behavior, deliver a patch."""
import copy
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath

from .generator import digest
from .repair_checks import CHECK_VERSION, assess, selected_checks
from .repair_runtime import DockerExecutor, STATUSES, validate_image

VERSION = "repository-repair/1"
DATA = Path(__file__).with_name("repair_data") / "packaging_state"


def make_case(image):
    validate_image(image)
    files = json.loads((DATA / "base.json").read_text(encoding="utf-8"))
    provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    actual = {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items()}
    if actual != provenance["file_sha256"]:
        raise ValueError("Upstream source snapshot fingerprint changed")
    return {"generator_version": VERSION, "family": "repository_repair", "profile": "packaging_state",
            "domain": "python_repository", "source_task_id": provenance["issue"],
            "base_commit": provenance["base_commit"], "files": files,
            "image_id": image, "check_version": CHECK_VERSION, "max_steps": 40, "max_checks": 8}


def suite(image):
    return {"generator_version": VERSION, "cases": [make_case(image)]}


def validate_case(case):
    if digest(case) != digest(make_case(case["image_id"])):
        raise ValueError("Repository task differs from its pinned source, runtime or contract")


def safe_path(name):
    return (isinstance(name, str) and bool(name) and "\\" not in name and ":" not in name
            and not PurePosixPath(name).is_absolute()
            and all(part not in ("", ".", "..") for part in name.split("/")))


class RepairEnvironment:
    def __init__(self, case, condition="open", *, recorded_calls=None, executor=None):
        if condition != "open":
            raise ValueError("Repository repair supports only open")
        self.case, self.files = copy.deepcopy(case), copy.deepcopy(case["files"])
        self.condition = condition
        self.history, self.calls = [], []
        self.recorded_calls = recorded_calls
        self.executor = executor
        self.revision = self.check_count = self.invalid_actions = self.blocked_actions = 0
        self.verified_revision = None
        self.done, self.reason = False, None
        self.last_result = {"kind": "start"}

    def contract(self):
        return {"protocol_version": 1, "contract_version": VERSION, "family": "repository_repair",
                "repository": "pypa/packaging (complete package source plus selected public docs/tests)",
                "task": "Fix Requirement serialization losing the specifier's explicit prereleases setting. "
                        "For example, set Requirement('foo>=1.0').specifier.prereleases=True; after a pickle "
                        "round trip it becomes None. Preserve True, False and automatic None across pickle "
                        "protocols 0-5, shallow copy and deep copy. Preserve name, extras, URL, specifier and marker. "
                        "Continue loading the existing string and legacy dictionary states. Invalid state "
                        "types and malformed requirement strings must still raise TypeError.",
                "success": "Deliver a source patch after all evaluator-owned behavioral checks pass at the "
                           "current revision. Changing repository tests cannot change acceptance. "
                           "A reproduction-only pass is insufficient. Every edit invalidates verification.",
                "actions": {
                    "list": {"command": "list"},
                    "read": {"command": "read", "target": {"path": "relative/path", "start": 1, "lines": 120}},
                    "search": {"command": "search", "target": "literal text"},
                    "edit": {"command": "edit", "target": {"path": "src/packaging/file.py",
                                                          "old": "unique exact existing text", "new": "replacement"}},
                    "test": {"command": "test", "target": "reproduction"},
                    "verify": {"command": "verify"},
                    "finish": {"command": "finish"}},
                "semantics": "All actions consume a step. Read at most 200 lines; search returns at most 30 "
                             "matching lines. Edit only existing src/packaging/*.py files, using a unique old "
                             "string; no shell, package installation or network. test runs the reported example. "
                             "verify runs the full behavioral acceptance set in a fresh isolated container. "
                             "Both use one check allowance; failures remain spent. Finish is irreversible.",
                "max_steps": self.case["max_steps"], "max_checks": self.case["max_checks"],
                "execution_limits": {"seconds_per_check": 20, "memory_mib": 256, "cpus": 1,
                                     "output_bytes": 262144, "network": False}}

    def changed_paths(self):
        return sorted(n for n in self.files if self.files[n] != self.case["files"][n])

    def observation(self):
        return {"revision": self.revision, "steps_remaining": self.case["max_steps"] - len(self.history),
                "checks_remaining": self.case["max_checks"] - self.check_count,
                "verified_current_state": self.verified_revision == self.revision,
                "changed_paths": self.changed_paths(), "result": copy.deepcopy(self.last_result)}

    def lower_bound(self):
        return None  # No invented optimum tool count for a real repair task.

    def _check(self, group):
        requests = [r["input"] for r in selected_checks(group)]
        binding = {"step": len(self.history) + 1, "revision": self.revision, "group": group,
                   "files_sha256": digest(self.files), "input_sha256": digest(requests),
                   "image_id": self.case["image_id"], "check_version": CHECK_VERSION}
        if self.recorded_calls is not None:
            if len(self.calls) >= len(self.recorded_calls):
                raise ValueError("Missing recorded code execution")
            call = self.recorded_calls[len(self.calls)]
            if set(call) != {*binding, "response"} or any(call[k] != v for k, v in binding.items()):
                raise ValueError("Code execution is not bound to this exact revision, input and runtime")
            response = copy.deepcopy(call["response"])
        else:
            runner = self.executor or DockerExecutor(self.case["image_id"])
            response = runner.run(copy.deepcopy(self.files), requests)
        if (not isinstance(response, dict) or response.get("status") not in STATUSES
                or set(response) != ({"status", "values"} if response["status"] == "completed" else {"status"})):
            raise ValueError("Invalid code execution record")
        outcome = assess(group, response)
        self.calls.append({**binding, "response": response})
        self.check_count += 1
        if group == "all":
            self.verified_revision = self.revision if outcome["passed"] else None
        return {"kind": "check", "group": group, "checked_revision": self.revision, **outcome}

    def step(self, action):
        if self.done:
            raise RuntimeError("Episode already ended")
        command = action.get("command") if isinstance(action, dict) else None
        target = action.get("target") if isinstance(action, dict) else None
        result = None
        if isinstance(command, str) and isinstance(action, dict):
            if set(action) == {"command"}:
                if command == "list":
                    result = {"kind": "files", "paths": sorted(self.files)}
                elif command == "finish":
                    self.done, self.reason = True, "finished"
                    result = {"kind": "finish"}
                elif command == "verify" and self.check_count < self.case["max_checks"]:
                    result = self._check("all")
                elif command == "verify":
                    result = {"kind": "blocked", "message": "Check allowance exhausted"}
            elif set(action) == {"command", "target"}:
                if command == "search" and isinstance(target, str) and 1 <= len(target) <= 200:
                    matches = [{"path": n, "line": i, "text": line[:300]}
                               for n in sorted(self.files) for i, line in enumerate(self.files[n].splitlines(), 1)
                               if target in line]
                    result = {"kind": "matches", "matches": matches[:30], "truncated": len(matches) > 30}
                elif command == "test" and target == "reproduction":
                    result = (self._check("reproduction") if self.check_count < self.case["max_checks"]
                              else {"kind": "blocked", "message": "Check allowance exhausted"})
                elif isinstance(target, dict) and safe_path(target.get("path")) and target["path"] in self.files:
                    path = target["path"]
                    if (command == "read" and set(target) == {"path", "start", "lines"}
                            and type(target["start"]) is int and target["start"] >= 1
                            and type(target["lines"]) is int and 1 <= target["lines"] <= 200):
                        lines = self.files[path].splitlines()
                        selected = lines[target["start"] - 1:target["start"] - 1 + target["lines"]]
                        result = {"kind": "file", "path": path, "start": target["start"],
                                  "total_lines": len(lines), "text": "\n".join(selected)}
                    elif (command == "edit" and set(target) == {"path", "old", "new"}
                          and path.startswith("src/packaging/") and path.endswith(".py")
                          and all(isinstance(target[k], str) and len(target[k]) <= 65536 for k in ("old", "new"))
                          and target["old"] and target["old"] != target["new"]
                          and self.files[path].count(target["old"]) == 1):
                        updated = self.files[path].replace(target["old"], target["new"], 1)
                        if len(updated.encode()) <= 600_000:
                            self.files[path] = updated
                            self.revision += 1
                            self.verified_revision = None
                            result = {"kind": "edited", "path": path, "revision": self.revision}
        if result is None:
            self.invalid_actions += 1
            result = {"kind": "invalid", "message": "Use the published action schema; edits need one exact match in a writable source file"}
        if result["kind"] == "blocked":
            self.blocked_actions += 1
        self.last_result = result
        if len(self.history) + 1 >= self.case["max_steps"] and not self.done:
            self.done, self.reason = True, "step_limit"
        self.history.append({"action": copy.deepcopy(action), "observation": None})
        self.history[-1]["observation"] = self.observation()
        return copy.deepcopy(self.history[-1]["observation"])

    def abort(self, reason="adapter_error"):
        self.done, self.reason = True, reason

    def grade(self):
        return {"success": self.done and self.reason == "finished" and self.verified_revision == self.revision
                           and bool(self.changed_paths()),
                "termination": self.reason, "cost": len(self.history), "budget": self.case["max_steps"],
                "steps": len(self.history), "verified_current_state": self.verified_revision == self.revision,
                "check_calls": self.check_count, "edited_files": len(self.changed_paths()), "revisions": self.revision,
                "invalid_actions": self.invalid_actions, "blocked_actions": self.blocked_actions,
                "code_execution_failures": sum(assess(c["group"], c["response"])["execution_status"] != "completed"
                                               for c in self.calls)}

    def evidence(self):
        lines = (line for n in self.changed_paths()
                 for line in difflib.unified_diff(self.case["files"][n].splitlines(keepends=True),
                                                  self.files[n].splitlines(keepends=True),
                                                  fromfile="a/" + n, tofile="b/" + n))
        patch = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                        for line in lines)
        return {"calls": copy.deepcopy(self.calls), "patch": patch, "final_files_sha256": digest(self.files)}
