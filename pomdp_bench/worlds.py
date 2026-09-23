"""Explicit dispatch for synthetic controls and real repository repair."""
from . import GENERATOR_VERSION, __version__, version_at_least
from .coverage import COVER_VERSIONS, DEPTH_VERSION, CoverageEnvironment, validate_case as validate_cover
from .environment import (Environment as DiagnosticEnvironment, CONDITIONS as DIAGNOSTIC_CONDITIONS,
                          validate_condition_version as validate_diagnostic_condition)
from .generator import validate_case as validate_diagnostic
from .repair import VERSION as REPAIR_VERSION, REPAIR_VERSIONS, RepairEnvironment, validate_case as validate_repair
from .incident import VERSION as INCIDENT_VERSION, IncidentEnvironment, validate_case as validate_incident

from .settlement import VERSION as SETTLEMENT_VERSION, SettlementEnvironment, validate_case as validate_settlement

from .reconciliation import VERSION as RECONCILIATION_VERSION, ReconciliationEnvironment, validate_case as validate_reconciliation

from .refund_recovery import VERSION as REFUND_VERSION, RefundEnvironment, validate_case as validate_refund

INCIDENT_VERSIONS = (INCIDENT_VERSION, SETTLEMENT_VERSION, RECONCILIATION_VERSION, REFUND_VERSION)

VERSIONS = (GENERATOR_VERSION, *COVER_VERSIONS, *REPAIR_VERSIONS, *INCIDENT_VERSIONS)
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
    elif version == REFUND_VERSION:
        validate_refund(case)
    elif version == RECONCILIATION_VERSION:
        validate_reconciliation(case)
    elif version == SETTLEMENT_VERSION:
        validate_settlement(case)
    elif version == INCIDENT_VERSION:
        validate_incident(case)
    else:
        raise ValueError("Unsupported environment generator")


def validate_case_version(case, framework_version):
    if case["generator_version"] == REFUND_VERSION and not version_at_least(framework_version, "2.12.0"):
        raise ValueError("Refund recovery requires framework 2.12")
    if case["generator_version"] == RECONCILIATION_VERSION and not version_at_least(framework_version, "2.11.0"):
        raise ValueError("Reconciliation repair requires framework 2.11")
    if case["generator_version"] == SETTLEMENT_VERSION and not version_at_least(framework_version, "2.10.0"):
        raise ValueError("External settlement requires framework 2.10")
    if case["generator_version"] == INCIDENT_VERSION and not version_at_least(framework_version, "2.9.0"):
        raise ValueError("Executable incident requires framework 2.9")
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
    if case["generator_version"] == REFUND_VERSION:
        return RefundEnvironment(case, condition, recorded_calls=recorded_calls)
    if case["generator_version"] == RECONCILIATION_VERSION:
        return ReconciliationEnvironment(case, condition, recorded_calls=recorded_calls)
    if case["generator_version"] == SETTLEMENT_VERSION:
        return SettlementEnvironment(case, condition, recorded_calls=recorded_calls)
    if case["generator_version"] == INCIDENT_VERSION:
        return IncidentEnvironment(case, condition, recorded_calls=recorded_calls)
    if case["generator_version"] == GENERATOR_VERSION:
        return DiagnosticEnvironment(case, condition, noise_seed)
    raise ValueError("Unsupported environment generator")


def cluster_id(case):
    from .generator import digest
    return digest([case["generator_version"], case["source_task_id"]
                   if case["generator_version"] in (*REPAIR_VERSIONS, *INCIDENT_VERSIONS) else case["seed"]])
