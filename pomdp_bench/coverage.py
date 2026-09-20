"""Versioned combinatorial planning, information acquisition and selective recovery."""
from __future__ import annotations

import copy
import math
import random
from functools import lru_cache

from . import __version__
from .generator import digest, keyed_seed

VERSION = "dependency-cover/1"
# Goals, maximum goals per operation, alternative operations. Labels are scales,
# not empirically established frontier-model difficulty rankings.
SCALES = {"sanity": (6, 2, 9), "challenge": (18, 3, 36),
          "hard": (32, 4, 64), "extreme": (48, 6, 96)}
POLICIES = ("cover_reference", "cover_greedy", "cover_rarest", "cover_no_recovery")


def generate(seed, profile="hard", *, recovery=True, slack=0):
    if profile not in SCALES:
        raise ValueError("Invalid coverage seed, scale or recovery flag")
    return _generate(seed, profile, SCALES[profile], VERSION, recovery=recovery, slack=slack)


def _generate(seed, profile, shape, version, *, recovery=True, slack=0):
    """Shared sampler; nonreleased shapes remain outside suite validation."""
    if type(seed) is not int or seed < 0 or type(recovery) is not bool:
        raise ValueError("Invalid coverage seed, scale or recovery flag")
    count, width, alternatives = shape
    if (any(type(n) is not int for n in shape) or not 2 <= width <= count <= 899
            or count % width or not count // width <= alternatives <= min(8999, math.comb(count, width))):
        raise ValueError("Invalid coverage dimensions")
    if type(slack) is not int or not 0 <= slack <= count:
        raise ValueError("Work slack must be an integer between zero and the goal count")
    rng = random.Random(keyed_seed(seed, version + "/" + profile))
    goals = [f"g-{n}" for n in rng.sample(range(100, 999), count)]
    rng.shuffle(goals)
    operations = [f"op-{n}" for n in rng.sample(range(1000, 9999), alternatives)]
    # A changed subset of fixed size; identity is private until its announced event.
    changed = set(rng.sample(goals, (count // width - 1) * width))
    epochs = []
    for epoch in range(2 if recovery else 1):
        groups = [goals[:]] if epoch == 0 else [[g for g in goals if g in changed],
                                               [g for g in goals if g not in changed]]
        rows = set()
        for group in groups:
            rng.shuffle(group)
            # Construct existence, never retain a privileged solution in the case.
            rows.update(tuple(sorted(group[i:i + width])) for i in range(0, len(group), width))
        while len(rows) < alternatives:
            rows.add(tuple(sorted(rng.sample(goals, width))))
        rows = sorted(rows)
        rng.shuffle(rows)
        epochs.append(dict(zip(operations, map(list, rows))))
    limits = [count // width + slack]
    if recovery:
        limits.append(len(changed) // width + slack)
    probes = alternatives * len(epochs)
    return {"generator_version": version, "seed": seed, "family": "dependency_cover", "profile": profile,
            "domain": "abstract", "recovery": recovery, "slack": slack, "goals": sorted(goals),
            "operations": sorted(operations), "epochs": epochs, "changed_goals": sorted(changed) if recovery else [],
            "width": width, "work_limits": limits, "inspection_budget": probes,
            "budget": probes + sum(limits) + len(epochs), "max_steps": probes + sum(limits) + 12}


def suite(seeds, profiles=("hard",), *, recovery=True, slack=0):
    if not seeds or len(set(seeds)) != len(seeds) or not profiles or len(set(profiles)) != len(profiles):
        raise ValueError("Use nonempty unique seeds and scales")
    return {"generator_version": VERSION, "cases": [generate(s, p, recovery=recovery, slack=slack)
                                                     for s in seeds for p in profiles]}


def validate_case(case):
    if digest(case) != digest(generate(case["seed"], case["profile"], recovery=case["recovery"], slack=case["slack"])):
        raise ValueError("Coverage case differs from its versioned generator")


def cover_plan(catalogue, missing, slots, *, node_limit=1_000_000):
    """Minimum additional work using revealed rows only. Exhaustion is not infeasibility."""
    goals = sorted(missing)
    bit = {g: 1 << i for i, g in enumerate(goals)}
    rows = [(name, sum(bit[g] for g in set(covers) & set(goals))) for name, covers in sorted(catalogue.items())]
    rows = [(name, mask) for name, mask in rows if mask]
    width = max((mask.bit_count() for _, mask in rows), default=1)
    if goals and len(goals) == width * slots:
        return _tight_cover(rows, len(goals), width, node_limit)
    nodes = 0

    @lru_cache(None)
    def search(left, remaining):
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            raise RuntimeError("Public reference search limit reached; no infeasibility claim")
        if not left:
            return ()
        if not remaining:
            return None
        usable = [(name, mask & left) for name, mask in rows if mask & left]
        if not usable or max(mask.bit_count() for _, mask in usable) * remaining < left.bit_count():
            return None
        # Under tight capacity, any overlap with already covered goals is impossible.
        largest = max(mask.bit_count() for _, mask in usable)
        usable = [(name, mask) for name, mask in usable
                  if mask.bit_count() + (remaining - 1) * largest >= left.bit_count()]
        choices = min(([row for row in usable if row[1] & (1 << i)]
                       for i in range(len(goals)) if left & (1 << i)), key=len)
        for name, mask in sorted(choices, key=lambda row: (-row[1].bit_count(), row[0])):
            tail = search(left & ~mask, remaining - 1)
            if tail is not None:
                return (name, *tail)
        return None

    target = (1 << len(goals)) - 1
    for limit in range(math.ceil(len(goals) / max((m.bit_count() for _, m in rows), default=1)), slots + 1):
        result = search(target, limit)
        if result is not None:
            return list(result), nodes
    return None, nodes


def _tight_cover(rows, goal_count, width, node_limit):
    """Exact-capacity case: every selected row must cover width fresh goals."""
    rows = [(name, mask) for name, mask in rows if mask.bit_count() == width]
    columns = [sum(1 << r for r, (_, mask) in enumerate(rows) if mask & (1 << g))
               for g in range(goal_count)]
    conflicts = []
    for _, mask in rows:
        conflict = 0
        while mask:
            bit = mask & -mask
            conflict |= columns[bit.bit_length() - 1]
            mask ^= bit
        conflicts.append(conflict)
    nodes = 0
    failed = set()

    def search(left, active):
        nonlocal nodes
        # active rows are determined by left; do not memoize duplicate states.
        if left in failed:
            return None
        nodes += 1
        if nodes > node_limit:
            raise RuntimeError("Public reference search limit reached; no infeasibility claim")
        if not left:
            return ()
        bits, choices, best = left, 0, len(rows) + 1
        while bits:
            bit = bits & -bits
            available = columns[bit.bit_length() - 1] & active
            count = available.bit_count()
            if count < best:
                choices, best = available, count
            if not count:
                break
            bits ^= bit
        while choices:
            bit = choices & -choices
            index = bit.bit_length() - 1
            name, mask = rows[index]
            tail = search(left ^ mask, active & ~conflicts[index])
            if tail is not None:
                return (name, *tail)
            choices ^= bit
        failed.add(left)
        return None

    plan = search((1 << goal_count) - 1, (1 << len(rows)) - 1)
    return list(plan) if plan is not None else None, nodes


class CoverageEnvironment:
    def __init__(self, case, condition="open", noise_seed=0, framework_version=__version__):
        if condition != "open":
            raise ValueError("Coverage supports only the open contract; diagnostic prompts do not apply")
        self.case = copy.deepcopy(case)
        self.framework_version = framework_version
        self.condition = condition
        self.epoch = self.spent = self.revision = self.inspections = self.work = 0
        self.verified_revision = None
        self.covered = set()
        self.catalogue = {}
        self.done = False
        self.reason = None
        self.history = []
        self.last_result = {"kind": "start"}
        self.metrics = {"invalid_actions": 0, "blocked_actions": 0, "work_spent": 0,
                        "redundant_probes": 0, "failed_verifications": 0, "external_changes": 0}

    def contract(self):
        result = {"protocol_version": 1, "family": "dependency_cover", "contract_version": VERSION,
                "task": "Deliver all goals under the inspection and work limits. Discover operation coverage, "
                        "choose a feasible combination, build, verify and finish.",
                "success": "All goals covered, PASS at the latest state revision, explicit finish within all limits.",
                "semantics": "Each operation covers exactly width goals. Probe reveals its current coverage; "
                             "only freshly probed operations can be built. Overlapping coverage wastes work. "
                             "Each operation built costs one work unit, including repeats. There are no refunds. "
                             "A complete cover exists within the published work limit after probing all rows. "
                             "A batch is atomic and costs the same resources as its members; it saves requests, "
                             "not work. Invalid/blocked actions consume a step but no resources. "
                             "Every build and external change invalidates verification.",
                "change_rule": ("The first passing verification triggers one announced change. Only the "
                                "announced goals lose coverage; other completed goals remain valid. All operation "
                                "descriptions expire and must be probed again. A new work allowance starts; "
                                "earlier costs remain spent. Restore the missing goals, verify again and finish."
                                if self.case["recovery"] else "No external change."),
                "actions": {"probe": "target=one operation ID or all; cost one inspection per row",
                            "build": "target=nonempty array of distinct freshly probed operation IDs; cost one work per ID",
                            "verify": "no target; cost one action point", "status": "no target; free",
                            "finish": "no target; irreversible handover"},
                "width": self.case["width"], "work_limits": self.case["work_limits"][:],
                "inspection_budget": self.case["inspection_budget"], "budget": self.case["budget"],
                "max_steps": self.case["max_steps"]}
        if self.framework_version != "2.5.0":
            result["contract_version"] = "dependency-cover-actions/2"
            result["response_format"] = {
                "probe_example": {"command": "probe", "target": "all"},
                "build_example": {"command": "build", "target": ["replace-with-observed-operation-ID"]},
                "verify_example": {"command": "verify"}, "finish_example": {"command": "finish"},
                "rule": "Return exactly one JSON object using command and, where required, target."}
        return result

    def observation(self):
        return {"epoch": self.epoch, "revision": self.revision,
                "remaining": self.case["budget"] - self.spent,
                "steps_remaining": self.case["max_steps"] - len(self.history),
                "inspections_remaining": self.case["inspection_budget"] - self.inspections,
                "work_remaining": self.case["work_limits"][self.epoch] - self.work,
                "goals": self.case["goals"][:], "covered": sorted(self.covered),
                "operations": self.case["operations"][:], "catalogue": copy.deepcopy(self.catalogue),
                "result": copy.deepcopy(self.last_result)}

    def lower_bound(self):
        missing = len(set(self.case["goals"]) - self.covered)
        required = math.ceil(missing / self.case["width"])
        required += int(self.verified_revision != self.revision)
        if self.case["recovery"] and self.epoch == 0:
            required += len(self.case["changed_goals"]) // self.case["width"] + 1
        return required

    def step(self, action):
        if self.done:
            raise RuntimeError("Episode already ended")
        command = action.get("command") if isinstance(action, dict) else None
        target = action.get("target") if isinstance(action, dict) else None
        rows = []
        cost = None
        if isinstance(action, dict) and isinstance(command, str):
            if command == "probe" and set(action) == {"command", "target"} and isinstance(target, str):
                rows = self.case["operations"] if target == "all" else [target]
                if all(row in self.case["operations"] for row in rows):
                    cost = len(rows)
            elif (command == "build" and set(action) == {"command", "target"}
                  and isinstance(target, list) and target and all(isinstance(t, str) for t in target)
                  and len(set(target)) == len(target) and all(t in self.catalogue for t in target)):
                rows, cost = target, len(target)
            elif command in ("verify", "status", "finish") and set(action) == {"command"}:
                cost = int(command == "verify")
        if cost is None:
            self.metrics["invalid_actions"] += 1
            result = {"kind": "invalid"}
            if self.framework_version != "2.5.0":
                result["message"] = ("Use command plus target where required: probe takes a known ID or all; "
                                     "build takes a nonempty array of distinct freshly probed IDs; "
                                     "verify, status and finish take no target.")
        elif (self.spent + cost > self.case["budget"]
              or command == "probe" and self.inspections + cost > self.case["inspection_budget"]
              or command == "build" and self.work + cost > self.case["work_limits"][self.epoch]):
            self.metrics["blocked_actions"] += 1
            result = {"kind": "blocked", "message": "Resource limit; no changes applied"}
        else:
            self.spent += cost
            result = {"kind": command}
            if command == "probe":
                self.inspections += cost
                self.metrics["redundant_probes"] += sum(row in self.catalogue for row in rows)
                for row in rows:
                    self.catalogue[row] = self.case["epochs"][self.epoch][row][:]
            elif command == "build":
                self.work += cost
                self.metrics["work_spent"] += cost
                self.covered.update(g for row in rows for g in self.catalogue[row])
                self.revision += 1
                self.verified_revision = None
            elif command == "verify":
                passed = self.covered == set(self.case["goals"])
                result.update(passed=passed, checked_revision=self.revision)
                self.verified_revision = self.revision if passed else None
                self.metrics["failed_verifications"] += int(not passed)
                if passed and self.case["recovery"] and self.epoch == 0:
                    self.epoch = 1
                    self.covered.difference_update(self.case["changed_goals"])
                    self.catalogue = {}
                    self.work = 0
                    self.revision += 1
                    self.verified_revision = None
                    self.metrics["external_changes"] += 1
                    result["change"] = {"invalidated_goals": self.case["changed_goals"][:], "revision": self.revision}
            elif command == "finish":
                self.done, self.reason = True, "finished"
        self.last_result = result
        if len(self.history) + 1 >= self.case["max_steps"] and not self.done:
            self.done, self.reason = True, "step_limit"
        self.history.append({"action": copy.deepcopy(action), "observation": None})
        self.history[-1]["observation"] = self.observation()
        return copy.deepcopy(self.history[-1]["observation"])

    def abort(self, reason="adapter_error"):
        self.done, self.reason = True, reason

    def grade(self):
        return {"success": self.done and self.reason == "finished" and self.covered == set(self.case["goals"])
                and self.verified_revision == self.revision and self.spent <= self.case["budget"],
                "termination": self.reason, "cost": self.spent, "budget": self.case["budget"],
                "steps": len(self.history), "verified_current_state": self.verified_revision == self.revision,
                "goals_completed": len(self.covered), "goals_total": len(self.case["goals"]),
                "inspection_cost": self.inspections, **self.metrics}


def policy_action(kind, request):
    if kind not in POLICIES:
        raise ValueError("Unknown coverage policy")
    observation, history = request["observation"], request["history"]
    if kind == "cover_no_recovery" and observation["epoch"]:
        return {"command": "finish"}
    missing = set(observation["goals"]) - set(observation["covered"])
    if not missing:
        passed = any(e["observation"]["result"].get("passed") and
                     e["observation"]["result"].get("checked_revision") == observation["revision"] for e in history)
        return {"command": "finish" if passed else "verify"}
    if len(observation["catalogue"]) != len(observation["operations"]):
        return {"command": "probe", "target": "all"}
    if observation["work_remaining"] <= 0:
        return {"command": "finish"}
    if kind in ("cover_reference", "cover_no_recovery"):
        plan, _ = cover_plan(observation["catalogue"], missing, observation["work_remaining"])
        return {"command": "build", "target": plan} if plan else {"command": "finish"}
    rows = {name: set(goals) & missing for name, goals in observation["catalogue"].items()}
    if kind == "cover_rarest":
        # A competent local heuristic: service the least-supported goal first.
        goal = min(sorted(missing), key=lambda g: sum(g in covers for covers in rows.values()))
        rows = {name: covers for name, covers in rows.items() if goal in covers}
    best = min(rows, key=lambda name: (-len(rows[name]), name))
    return {"command": "build", "target": [best]}
