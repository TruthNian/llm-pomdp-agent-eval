# Security policy

## Reporting

Please report vulnerabilities privately through GitHub's security-advisory feature for this repository. Do not open a public issue containing credentials or an exploitable path.

## Scope

Security-relevant areas include:

- exposure of per-episode bearer tokens;
- unintended network binding beyond `127.0.0.1`;
- path traversal through run identifiers;
- accidental inclusion of raw event streams or credentials;
- model access to hidden simulator state;
- unsafe changes to subprocess invocation.

The simulator controls synthetic local state only. It must not be pointed at production infrastructure.
