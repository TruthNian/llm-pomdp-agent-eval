"""Information-respecting reference planner; no access to sampled answers.

Exact minimax tree over *reliable diagnostic tests*, followed by a known repair.
This is a restricted policy class, not a globally optimal noisy POMDP solver.
"""
from functools import lru_cache


def diagnostic_plan(stage: dict, candidates=None) -> tuple[int, dict]:
    repairs = {c["id"]: c["repair_cost"] for c in stage["candidates"]}
    tests = [t for t in stage["tests"] if t["accuracy"] == 1.0]
    initial = tuple(sorted(repairs if candidates is None else candidates))
    if not initial or not set(initial) <= repairs.keys():
        raise ValueError("Candidates must be a nonempty subset of the public hypotheses")

    @lru_cache(None)
    def solve(possible):
        if len(possible) == 1:
            return repairs[possible[0]], {"command": "repair", "target": possible[0]}
        best = None
        for test in tests:
            yes = tuple(c for c in possible if c in test["positive_for"])
            no = tuple(c for c in possible if c not in test["positive_for"])
            if not yes or not no:
                continue
            cost = test["cost"] + max(solve(yes)[0], solve(no)[0])
            # Stable tie-breaking is independent of catalogue order.
            key = (cost, test["id"])
            if best is None or key < best[0]:
                best = (key, {"command": "inspect", "target": test["id"]})
        if best is None:
            raise ValueError("Reliable tests cannot distinguish all candidates")
        return best[0][0], best[1]

    return solve(initial)


def consistent_candidates(observation: dict, history: list[dict]) -> set[str]:
    stage = observation["catalogue"]
    possible = {c["id"] for c in stage["candidates"]}
    tests = {t["id"]: t for t in stage["tests"]}
    for event in history:
        result = event["observation"]["result"]
        if result.get("kind") != "test" or result.get("phase") != observation["phase"]:
            continue
        test = tests.get(result["test"])
        if not test or test["accuracy"] != 1.0:
            continue
        positive = set(test["positive_for"])
        possible &= positive if result["positive"] else possible - positive
    return possible
