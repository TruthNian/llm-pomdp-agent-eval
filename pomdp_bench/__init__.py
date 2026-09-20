"""Public-observation agent evaluation. Historical v1 lives in harness/."""

__version__ = "2.6.0"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "diagnostic-graphs/1"
# The diagnostic kernel is unchanged; 2.5 adds a separately versioned family.
REPLAY_VERSIONS = ("2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "2.5.0", "2.5.1", "2.5.2", "2.5.3", "2.6.0")


def version_at_least(version, minimum):
    """Only known replay versions can enable a versioned feature."""
    return version in REPLAY_VERSIONS and REPLAY_VERSIONS.index(version) >= REPLAY_VERSIONS.index(minimum)
