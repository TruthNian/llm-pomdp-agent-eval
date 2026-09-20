"""A narrow, preregistered two-condition study over the existing collector."""
from __future__ import annotations

import itertools
import math
import re
import secrets
from collections import defaultdict
from statistics import mean, stdev

from . import GENERATOR_VERSION, __version__, version_at_least
from .agents import validate_agent_version, validate_config
from .environment import PROMPTS
from .generator import DOMAINS, FAMILIES, PROFILES, digest, suite
from .interventions import CONTROL, CONTRAST, INTERVENTION_ID, TREATMENT

ANALYSIS_VERSION = "paired-seed-hoeffding/1"
ORDER_VERSION = "paired-counterbalance/1"
CENSORED = {"adapter_error", "internal_error", "collection_interrupted", "wall_limit"}
PLAN_FIELDS = {"schema_version", "framework_version", "generator_version", "study_id", "purpose", "hypothesis",
               "intervention", "primary_outcome", "minimum_useful_effect", "precision", "independent_seeds",
               "task_distribution", "replicates", "agents", "wall_seconds", "stopping_rule", "failure_policy"}


def required_seeds(confidence, half_width, comparisons):
    """D_seed in [-1,1]; two-sided Hoeffding + union bound across declared agents."""
    try:
        return math.ceil(2 * math.log(2 * comparisons / (1 - confidence)) / half_width ** 2)
    except (OverflowError, ZeroDivisionError):
        raise ValueError("Requested precision is outside the representable planning range") from None


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS:
        raise ValueError("Study plan has missing or unknown fields")
    fixed = {"schema_version": 1, "generator_version": GENERATOR_VERSION,
             "intervention": INTERVENTION_ID, "primary_outcome": "accepted_completion",
             "stopping_rule": "fixed_matrix", "failure_policy": "retain_and_bound"}
    if (type(plan["schema_version"]) is not int or not version_at_least(plan["framework_version"], "2.2.0")
            or any(plan[k] != v for k, v in fixed.items())):
        raise ValueError("Unsupported study version, intervention, outcome or collection policy")
    if not isinstance(plan["study_id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", plan["study_id"]):
        raise ValueError("study_id must be a short lowercase identifier")
    if not isinstance(plan["hypothesis"], str) or not plan["hypothesis"].strip():
        raise ValueError("Declare the hypothesis before collection")
    if plan["purpose"] not in ("pilot", "confirmatory"):
        raise ValueError("Study purpose must be pilot or confirmatory")
    for field in ("independent_seeds", "replicates"):
        if type(plan[field]) is not int or plan[field] < 1:
            raise ValueError(f"{field} must be a positive integer")
    for field in ("minimum_useful_effect", "wall_seconds"):
        if type(plan[field]) not in (float, int) or not math.isfinite(plan[field]) or plan[field] <= 0:
            raise ValueError(f"{field} must be finite and positive")
    if plan["minimum_useful_effect"] > 1:
        raise ValueError("Minimum effect is an absolute success-rate difference in (0,1]")
    precision = plan["precision"]
    if not isinstance(precision, dict) or set(precision) != {"confidence", "half_width"}:
        raise ValueError("Specify confidence and half_width, without an adaptive analysis method")
    for value in precision.values():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
            raise ValueError("Precision settings must be finite numbers in (0,1)")
    if precision["half_width"] > plan["minimum_useful_effect"] / 2:
        raise ValueError("Target half-width must be at most half the minimum useful effect")
    distribution = plan["task_distribution"]
    if not isinstance(distribution, dict) or set(distribution) != {"families", "profiles", "domains"}:
        raise ValueError("Declare the complete task distribution")
    for key, allowed in (("families", FAMILIES), ("profiles", PROFILES), ("domains", DOMAINS)):
        values = distribution[key]
        if (not isinstance(values, list) or not values or any(not isinstance(x, str) for x in values)
                or len(set(values)) != len(values) or set(values) - set(allowed)):
            raise ValueError("Unknown or duplicate task-distribution values")
    agents = plan["agents"]
    if not isinstance(agents, list) or not agents:
        raise ValueError("Declare named agent configurations")
    for agent in agents:
        validate_config(agent)
        validate_agent_version(agent, plan["framework_version"])
    if len({a["name"] for a in agents}) != len(agents):
        raise ValueError("Study agent names must be unique")
    required = required_seeds(precision["confidence"], precision["half_width"], len(agents))
    if plan["purpose"] == "confirmatory" and plan["independent_seeds"] < required:
        raise ValueError(f"Confirmatory precision requires at least {required} independent seeds; repeats cannot substitute")
    return required


def bind_plan(plan):
    validate_plan(plan)
    return {"plan": plan, "plan_sha256": digest(plan), "analysis_version": ANALYSIS_VERSION,
            "schedule_version": ORDER_VERSION,
            "prompt_sha256": digest({c: PROMPTS[c] for c in CONTRAST})}


def validate_binding(binding, data, configs, conditions, replicates, wall_seconds):
    plan = binding["plan"]
    if binding != bind_plan(plan):
        raise ValueError("Study plan, analysis, schedule or prompt fingerprint changed")
    if (configs != plan["agents"] or conditions != list(CONTRAST) or replicates != plan["replicates"]
            or wall_seconds != plan["wall_seconds"] or data["generator_version"] != plan["generator_version"]):
        raise ValueError("Study plan does not match the execution definition")
    seeds = {c["seed"] for c in data["cases"]}
    dims = plan["task_distribution"]
    expected = set(itertools.product(seeds, dims["families"], dims["profiles"], dims["domains"]))
    actual = {(c["seed"], c["family"], c["profile"], c["domain"]) for c in data["cases"]}
    if len(seeds) != plan["independent_seeds"] or actual != expected or len(actual) != len(data["cases"]):
        raise ValueError("Study seed count or complete task distribution changed")


def prepare_study(plan, output):
    from .collection import prepare_suite
    validate_plan(plan)
    if output.exists():
        raise ValueError("Output directory already exists; a study plan cannot replace an earlier collection")
    if plan["framework_version"] != __version__:
        raise ValueError("Prepare studies with the declared framework version")
    # Draw only after accepting the plan; no hand-selected evaluation suite or seed search.
    seeds = []
    seen = set()
    while len(seeds) < plan["independent_seeds"]:
        seed = secrets.randbits(128)
        if seed not in seen:
            seeds.append(seed)
            seen.add(seed)
    data = suite(seeds, **plan["task_distribution"])
    return prepare_suite(data, plan["agents"], list(CONTRAST), plan["replicates"], output,
                         plan["wall_seconds"], study=bind_plan(plan))


def analyze_study(manifest, records):
    """Called after complete collection validation; contrasts are fixed by the bound plan."""
    binding = manifest["study"]
    plan = binding["plan"]
    required = validate_plan(plan)
    names = [a["name"] for a in plan["agents"]]
    # Still reject ambiguous/unpaired input when the pure analysis is used directly.
    by_key = {(r["agent"]["name"], r["case_id"], r["replicate"], r["condition"]): r for r in records}
    cases = {digest(c): c for c in manifest["cases"]}
    expected = set(itertools.product(names, cases, range(plan["replicates"]), CONTRAST))
    if len(by_key) != len(records) or set(by_key) != expected:
        raise ValueError("Study analysis requires exactly the complete paired matrix")
    n = plan["independent_seeds"]
    confidence = plan["precision"]["confidence"]
    radius = math.sqrt(2 * math.log(2 * len(names) / (1 - confidence)) / n)
    comparisons = []
    for name in names:
        clusters = defaultdict(list)
        counts = {c: {"accepted": 0, "episodes": 0, "censored": 0,
                      "observed_task_failures": 0, "observed_budget_losses": 0} for c in CONTRAST}
        for cid, case in cases.items():
            for replicate in range(plan["replicates"]):
                control, treatment = [by_key[name, cid, replicate, cond] for cond in CONTRAST]
                for row in (control, treatment):
                    group = counts[row["condition"]]
                    censored = row["grade"]["termination"] in CENSORED
                    group["episodes"] += 1
                    group["accepted"] += int(row["grade"]["success"])
                    group["censored"] += int(censored)
                    group["observed_task_failures"] += int(not row["grade"]["success"] and not censored)
                    group["observed_budget_losses"] += int(row["grade"]["budget_lost_at"] is not None)
                a, b = int(treatment["grade"]["success"]), int(control["grade"]["success"])
                ua = treatment["grade"]["termination"] in CENSORED
                ub = control["grade"]["termination"] in CENSORED
                clusters[case["seed"]].append((a - b, (0 if ua else a) - (1 if ub else b),
                                              (1 if ua else a) - (0 if ub else b)))
        if len(clusters) != n:
            raise ValueError("Analysis seed count differs from the plan")
        seed_values = [tuple(mean(x[i] for x in values) for i in range(3)) for values in clusters.values()]
        effect, lower, upper = [mean(x[i] for x in seed_values) for i in range(3)]
        interval = [max(-1.0, effect - radius), min(1.0, effect + radius)]
        censored = sum(v["censored"] for v in counts.values())
        if plan["purpose"] == "pilot":
            decision = "exploratory_only"
        elif interval[0] >= plan["minimum_useful_effect"]:
            decision = "minimum_operational_gain_supported"
        elif interval[1] < plan["minimum_useful_effect"]:
            decision = "minimum_operational_gain_excluded"
        else:
            decision = "inconclusive"
        gate = ("resolve_execution_censoring" if censored else
                "no_observed_baseline_headroom" if counts[CONTROL]["observed_task_failures"] == 0 else
                "no_observed_budget_failure" if counts[CONTROL]["observed_budget_losses"] == 0 else
                "target_failure_observed")
        comparisons.append({"agent": name, "contrast": f"{TREATMENT}-minus-{CONTROL}", "seed_clusters": n,
            "pairs": len(cases) * plan["replicates"], "observed_success_difference": effect,
            "simultaneous_hoeffding_interval": interval,
            "seed_difference_stddev": stdev(x[0] for x in seed_values) if n > 1 else None,
            "censoring_identification_bounds": [lower, upper],
            "condition_counts": counts, "decision": decision, "pilot_gate": gate,
            "mechanism_claim_eligible": False})
    return {"plan_sha256": binding["plan_sha256"], "analysis_version": ANALYSIS_VERSION,
            "purpose": plan["purpose"], "primary_outcome": plan["primary_outcome"],
            "confidence": confidence, "interval_half_width_before_clipping": radius,
            "required_seeds_for_declared_precision": required,
            "declared_precision_met": n >= required, "primary_comparisons": comparisons,
            "interpretation": [
                "Each primary contrast compares two prompts within one agent; there is no cross-model primary ranking.",
                "Average within each seed, then weight seeds equally. Repeats and skins do not create independent samples.",
                "Hoeffding intervals assume independent seed-level outcomes under a stable collection process; alpha is divided across declared agents.",
                "The precision bound is conservative and is not a power calculation or an optional-stopping guarantee.",
                "Censoring bounds replace interrupted outcomes by all possible binary outcomes; these are identification bounds, not confidence intervals.",
                "Failure-inclusive delivery effects, reminder sensitivity and an internal reasoning mechanism are different claims.",
                "A pilot cannot support a confirmatory claim; ceiling or absent target failures call for reconsidering the task before scaling."]}
