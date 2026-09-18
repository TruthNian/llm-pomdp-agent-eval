"""Versioned structural generation. Private randomness never reaches an agent."""
from __future__ import annotations

import hashlib
import hmac
import json
import random

from . import GENERATOR_VERSION
from .planning import diagnostic_plan

FAMILIES = ("diagnosis", "cascade")
PROFILES = ("standard", "wide", "deep")
DOMAINS = ("incident", "data_pipeline")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def keyed_seed(seed: int, label: str) -> int:
    return int.from_bytes(hmac.new(str(seed).encode(), label.encode(), hashlib.sha256).digest(), "big")


def generate(seed: int, family="diagnosis", profile="standard", domain="incident") -> dict:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if family not in FAMILIES or profile not in PROFILES or domain not in DOMAINS:
        raise ValueError("Unknown family, profile, or domain")
    # Domain is deliberately absent from these streams: skins share latent structure.
    rng = random.Random(keyed_seed(seed, f"{GENERATOR_VERSION}/{family}/{profile}/structure"))
    private = random.Random(keyed_seed(seed, f"{GENERATOR_VERSION}/{family}/{profile}/answers"))
    size = rng.randint(3, 5) if profile != "wide" else rng.randint(6, 8)
    phases = 1 if family == "diagnosis" else (3 if profile == "deep" else 2)
    stages, truths = [], []
    for phase in range(phases):
        ids = rng.sample(range(1000, 9999), size)
        candidates = [{"id": f"h-{i}", "repair_cost": rng.randint(3, 7)} for i in ids]
        names = [c["id"] for c in candidates]
        masks = {frozenset([name]) for name in names}
        for _ in range(size):
            masks.add(frozenset(rng.sample(names, rng.randint(1, size - 1))))
        tests = []
        for i, subset in enumerate(sorted(masks, key=lambda s: tuple(sorted(s)))):
            tests.append({"id": f"t-{phase}-{i}", "positive_for": sorted(subset),
                          "cost": rng.randint(2, 5), "accuracy": 1.0})
        # Cheap noisy evidence has repeatable, independently keyed noise.
        for i in range(2):
            tests.append({"id": f"s-{phase}-{i}",
                          "positive_for": sorted(rng.sample(names, rng.randint(1, size - 1))),
                          "cost": 1, "accuracy": rng.choice([0.65, 0.8])})
        # A declared, uninformative check measures checklist-following behavior.
        tests.append({"id": f"d-{phase}", "positive_for": names[:], "cost": 1, "accuracy": 1.0})
        rng.shuffle(tests)
        rng.shuffle(candidates)
        stages.append({"candidates": candidates, "tests": tests})
        truths.append(private.choice(names))
    verify_cost = rng.randint(2, 4)
    rollback_cost = rng.randint(1, 3)
    stage_bounds = [diagnostic_plan(s)[0] for s in stages]
    # Bound uses public structures and ALL possible truths, never the sampled answer.
    budget = sum(stage_bounds) + verify_cost + rng.randint(0, 3)
    return {"generator_version": GENERATOR_VERSION, "seed": seed, "family": family,
            "profile": profile, "domain": domain, "stages": stages, "truths": truths,
            "stage_bounds": stage_bounds, "budget": budget, "verify_cost": verify_cost,
            "rollback_cost": rollback_cost, "max_steps": 100}


def suite(seeds: list[int], families=FAMILIES, profiles=("standard",), domains=("incident",)) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Use a nonempty list of unique seeds")
    for values in (families, profiles, domains):
        if not values or len(set(values)) != len(values):
            raise ValueError("Suite dimensions must be nonempty and unique")
    cases = [generate(seed, family, profile, domain) for seed in seeds
             for family in families for profile in profiles for domain in domains]
    return {"generator_version": GENERATOR_VERSION, "cases": cases}


def validate_case(case: dict) -> None:
    expected = generate(case["seed"], case["family"], case["profile"], case["domain"])
    if digest(case) != digest(expected):
        raise ValueError("Case does not match its versioned generator; use a new generator version")
