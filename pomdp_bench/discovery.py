"""Versioned offline discovery/recovery prototype; not a scored family."""
from __future__ import annotations

import copy

VERSION = "dependency-recovery/1"
BUDGET = 12
MAX_STEPS = 20
COSTS = {"probe": 1, "prepare": 2, "assemble": 2, "verify": 1, "status": 0, "finish": 0}


def validate_fixture(fixture):
    if not isinstance(fixture, dict) or set(fixture) != {"handles", "visible", "changing"}:
        raise ValueError("Invalid discovery fixture")
    handles = fixture["handles"]
    if (not isinstance(handles, list) or len(handles) != 2
            or any(not isinstance(h, str) or not h.strip() for h in handles)
            or handles[0] == handles[1]
            or any(type(fixture[k]) is not bool for k in ("visible", "changing"))):
        raise ValueError("Use two distinct handles and boolean ablations")


class DiscoveryEnvironment:
    def __init__(self, fixture):
        validate_fixture(fixture)
        self.fixture = copy.deepcopy(fixture)
        self.changed = False
        self.dependency = fixture["handles"][0] if fixture["visible"] else None
        self.known = {self.dependency} if self.dependency else set()
        self.prepared = self.assembly = None
        self.revision = self.spent = 0
        self.verified_revision = None
        self.done = False
        self.reason = None
        self.history = []
        self.last_result = {"kind": "start"}
        self.metrics = {"probes": 0, "redundant_probes": 0, "invalid_actions": 0,
                        "stale_actions": 0, "prerequisite_blocks": 0, "budget_blocks": 0,
                        "failed_verifications": 0}

    @property
    def current(self):
        return self.fixture["handles"][int(self.changed)]

    def contract(self):
        return {
            "contract_version": VERSION,
            "task": "Prepare the required dependency, assemble the deliverable, verify it and finish.",
            "success": "Explicit finish with current dependency preparation and assembly, a PASS at the "
                       "latest world revision, and both budgets respected.",
            "semantics": "One dependency is active. Probe reveals its preparation handle. Only revealed "
                         "handles can be prepared. Assembly requires current evidence and preparation. "
                         "Every prepare, assemble and external change invalidates verification. "
                         "Invalid, stale, unmet-prerequisite and unaffordable actions cost no points "
                         "but consume a step. Other actions also consume a step; finish is irreversible.",
            "change_rule": ("Immediately after the first passing verification, the dependency is replaced "
                            "once. PASS refers to the old revision. The change is announced and makes "
                            "the old handle, preparation, assembly and verification obsolete. Probe "
                            "reveals the replacement handle; rebuild and verify again."
                            if self.fixture["changing"] else "No external changes occur."),
            "actions": {"probe": "Reveal the current dependency handle", "prepare": "target=revealed handle",
                        "assemble": "Build using the current prepared dependency", "verify": "Check the result",
                        "status": "Read public state", "finish": "Submit and end"},
            "response_format": {"command": "action name", "target": "only for prepare"},
            "costs": dict(COSTS), "budget": BUDGET, "max_steps": MAX_STEPS,
        }

    def observation(self):
        return {"remaining": BUDGET - self.spent, "steps_remaining": MAX_STEPS - len(self.history),
                "revision": self.revision, "dependency": self.dependency,
                "dependency_stale": self.dependency is not None and self.dependency != self.current,
                "prepared": self.prepared, "assembly": self.assembly,
                "result": copy.deepcopy(self.last_result)}

    def _mutate(self):
        self.revision += 1
        self.verified_revision = None

    def step(self, action):
        if self.done:
            raise RuntimeError("Episode already ended")
        command = action.get("command") if isinstance(action, dict) else None
        target = action.get("target") if isinstance(action, dict) else None
        valid = (isinstance(action, dict) and isinstance(command, str) and command in COSTS
                 and ((command == "prepare" and set(action) == {"command", "target"}
                       and isinstance(target, str) and target in self.known)
                      or (command != "prepare" and set(action) == {"command"})))
        if not valid:
            result = {"kind": "invalid"}
            self.metrics["invalid_actions"] += 1
        elif command == "prepare" and target != self.current:
            result = {"kind": "stale_dependency"}
            self.metrics["stale_actions"] += 1
        elif command == "assemble" and (self.dependency != self.current or self.prepared != self.current):
            result = {"kind": "unresolved_dependency"}
            self.metrics["prerequisite_blocks"] += 1
        elif self.spent + COSTS[command] > BUDGET:
            result = {"kind": "budget_blocked"}
            self.metrics["budget_blocks"] += 1
        else:
            self.spent += COSTS[command]
            result = {"kind": command}
            if command == "probe":
                self.metrics["probes"] += 1
                self.metrics["redundant_probes"] += int(self.dependency == self.current)
                self.dependency = self.current
                self.known.add(self.current)
            elif command == "prepare":
                self.prepared = target
                self._mutate()
            elif command == "assemble":
                self.assembly = self.current
                self._mutate()
            elif command == "verify":
                passed = self.prepared == self.current and self.assembly == self.current
                self.verified_revision = self.revision if passed else None
                self.metrics["failed_verifications"] += int(not passed)
                result.update(passed=passed, checked_revision=self.revision)
                if passed and self.fixture["changing"] and not self.changed:
                    self.changed = True
                    self._mutate()
                    result["change"] = {"kind": "dependency_replaced", "revision": self.revision}
            elif command == "finish":
                self.done, self.reason = True, "finished"
        self.last_result = result
        if len(self.history) + 1 >= MAX_STEPS and not self.done:
            self.done, self.reason = True, "step_limit"
        event = {"action": copy.deepcopy(action), "observation": None}
        self.history.append(event)
        event["observation"] = self.observation()
        return copy.deepcopy(event["observation"])

    def grade(self):
        current_verified = self.verified_revision == self.revision
        success = (self.done and self.reason == "finished" and self.prepared == self.current
                   and self.assembly == self.current and current_verified
                   and self.spent <= BUDGET and len(self.history) <= MAX_STEPS)
        return {"success": success, "termination": self.reason, "cost": self.spent,
                "steps": len(self.history), "verified_current_state": current_verified,
                "external_changes": int(self.changed), "recovered_after_change": self.changed and success,
                **self.metrics}
