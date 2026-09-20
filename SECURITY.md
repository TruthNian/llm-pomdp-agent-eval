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

Synthetic families control local simulated state. Repository repair executes
candidate code only inside the declared Docker runtime, without host mounts,
forwarded credentials or network. It must not be pointed at production infrastructure.

## V2 observation boundary

The HTTP adapter sends an allowlisted public JSON request and exposes no host
filesystem or shell to the remote model. Repair actions access only the selected
task workspace. Hidden truth, seeds, identifiers, manifests and grader source
remain evaluator-side. Credentials are omitted from traces; credential-bearing
URLs and redirects are rejected. No raw provider response/error bodies are persisted.

See the [repair execution boundary](docs/REPOSITORY_REPAIR.md#execution-and-evidence).
The evaluator never imports candidate code; pickle operations run in the container.
Docker and the evaluator host are trusted. Fixed behavioral controls are not a
claim of resistance to all hostile source or worker-output spoofing.

The `private/` output subtree contains seeds, answers and full audit trajectories. A name and `.gitignore` do not provide access control: keep it off agent-accessible hosts/mounts during evaluation. Do not expose the evaluator filesystem or environment through another tool while claiming this observation boundary.

Scripted policies are trusted Python code within the evaluator process. New local policies could inspect process memory or files regardless of the public `act()` interface. Untrusted local agents need a separate isolated service/container with no evaluator mounts, credentials, or process access. This repository does not claim OS isolation for in-process plugins.

The frozen v1 Codex runner defaults to broad filesystem access. It also uses answer-bearing workspace names. See [historical validity notes](studies/2026-gpt56-glm53/ERRATA.md); use v2 for new blind evaluations.

Replay verifies internal consistency of actions, observations and grades. It does not authenticate an adversarial evaluator or prove that reported provider usage is a genuine billing record.
