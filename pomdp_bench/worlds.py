"""Explicit dispatch for synthetic controls and real repository repair."""
from . import GENERATOR_VERSION, __version__, version_at_least
from .coverage import COVER_VERSIONS, DEPTH_VERSION, CoverageEnvironment, validate_case as validate_cover
from .environment import (Environment as DiagnosticEnvironment, CONDITIONS as DIAGNOSTIC_CONDITIONS,
                          validate_condition_version as validate_diagnostic_condition)
from .generator import validate_case as validate_diagnostic
from .repair import VERSION as REPAIR_VERSION, REPAIR_VERSIONS, RepairEnvironment, validate_case as validate_repair

VERSIONS = (GENERATOR_VERSION, *COVER_VERSIONS, *REPAIR_VERSIONS)
CONDITIONS = (*DIAGNOSTIC_CONDITIONS, "solver_assisted")


def validate_condition_version(condition, framework_version):
    if condition == "solver_assisted":
        if not version_at_least(framework_version, "2.6.0"):
            raise ValueError("Solver assistance requires framework 2.6")
    else:
        validate_diagnostic_condition(condition, framework_version)


def validate_case(case):
    version = case.get("generator_version") if isinstance(case, dict) else None
    if version == GENERATOR_VERSION:
        validate_diagnostic(case)
    elif version in COVER_VERSIONS:
        validate_cover(case)
    elif version in REPAIR_VERSIONS:
        validate_repair(case)
    else:
        raise ValueError("Unsupported environment generator")


def validate_case_version(case, framework_version):
    if case["generator_version"] in REPAIR_VERSIONS:
        minimum = "2.7.0" if case["generator_version"] == REPAIR_VERSION else "2.8.0"
        if not version_at_least(framework_version, minimum):
            raise ValueError("Repository repair requires framework " + minimum)
    minimum = "2.6.0" if case["generator_version"] == DEPTH_VERSION else "2.5.0"
    if case["generator_version"] in COVER_VERSIONS and not version_at_least(framework_version, minimum):
        raise ValueError(f"Dependency coverage requires framework {minimum}")


def Environment(case, condition="open", noise_seed=0, *, framework_version=__version__, recorded_calls=None):
    validate_case_version(case, framework_version)
    validate_condition_version(condition, framework_version)
    if case["generator_version"] in COVER_VERSIONS:
        return CoverageEnvironment(case, condition, noise_seed, framework_version)
    if case["generator_version"] in REPAIR_VERSIONS:
        return RepairEnvironment(case, condition, recorded_calls=recorded_calls)
    if case["generator_version"] == GENERATOR_VERSION:
        return DiagnosticEnvironment(case, condition, noise_seed)
    raise ValueError("Unsupported environment generator")


def cluster_id(case):
    from .generator import digest
    return digest([case["generator_version"], case["source_task_id"] if case["generator_version"] in REPAIR_VERSIONS else case["seed"]])
