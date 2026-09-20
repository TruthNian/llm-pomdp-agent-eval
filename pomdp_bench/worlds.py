"""Explicit dispatch for two independent kernels; no plugin registry."""
from . import GENERATOR_VERSION, __version__
from .coverage import VERSION as COVER_VERSION, CoverageEnvironment, validate_case as validate_cover
from .environment import Environment as DiagnosticEnvironment
from .generator import validate_case as validate_diagnostic

VERSIONS = (GENERATOR_VERSION, COVER_VERSION)


def validate_case(case):
    version = case.get("generator_version") if isinstance(case, dict) else None
    if version == GENERATOR_VERSION:
        validate_diagnostic(case)
    elif version == COVER_VERSION:
        validate_cover(case)
    else:
        raise ValueError("Unsupported environment generator")


def validate_case_version(case, framework_version):
    if case["generator_version"] == COVER_VERSION and framework_version not in ("2.5.0", "2.5.1", "2.5.2", "2.5.3"):
        raise ValueError("Dependency coverage requires framework 2.5")


def Environment(case, condition="open", noise_seed=0, *, framework_version=__version__):
    if case["generator_version"] == COVER_VERSION:
        return CoverageEnvironment(case, condition, noise_seed, framework_version)
    if case["generator_version"] == GENERATOR_VERSION:
        return DiagnosticEnvironment(case, condition, noise_seed)
    raise ValueError("Unsupported environment generator")
