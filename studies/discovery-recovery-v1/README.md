# Discovery/recovery contract validation 1

Date: 2026-09-20. Contract: `dependency-recovery/1`.
Scope: **public, deterministic development controls; no model requests**.
[Specification and transition rules](../../docs/DISCOVERY_RECOVERY.md).

## Decision and complete evidence

The minimal discovery/recovery contract passes its offline falsification gate.
Keep the narrow structure for the next design step. Do not yet register a scored
family, scale model collection, or claim arbitrary hypothesis discovery or
real-work prediction.

[controls.json](controls.json) contains **all 60 trajectories**, including every
failed control, exact public inputs, actions, observations, grades, fixture
definitions and the two prototype source SHA-256 hashes. Hashes normalize CRLF to
LF to make the same source portable across the CI operating systems. Source
binding and replay are consistency checks, not adversarial attestation.

Three handle-pair fixtures × two initial visibility states × two replacement
states × five scripted policies = 60 planned and retained episodes. Two fixtures
share an initial handle with different future handles. Relabelings are not
independent research samples. No seed-population intervals, model comparisons,
tokens or human-supervision measurements are inferred.

## Ablations

All fixtures have 12 action points and 20 steps. Each table cell covers all three
handle pairs; PASS is accepted delivery after current-state verification.

| Policy | Visible / stable | Hidden / stable | Visible / changing | Hidden / changing |
|---|---:|---:|---:|---:|
| Adaptive public-information witness | 3/3 | 3/3 | 3/3 | 3/3 |
| Freeze the initial action plan | 3/3 | 0/3 | 0/3 | 0/3 |
| Discover once, finish after the first PASS | 3/3 | 3/3 | 0/3 | 0/3 |
| Finish immediately after assembly | 0/3 | 0/3 | 0/3 | 0/3 |
| Probe until the budget is exhausted | 0/3 | 0/3 | 0/3 | 0/3 |
| Adaptive witness action points | 5 | 6 | 11 | 12 |

The important check is the rescue: a static plan succeeds with its missing
information supplied and no change; a policy that discovers but never revises
succeeds when replacement is removed. The changing task reports a genuine PASS
on an earlier revision, then announces that both its evidence and completed work
are obsolete. Following the old plan cannot recover. The witness probes for the
new operation, prepares it, rebuilds and verifies again before finishing.

The replacement is deterministic, occurs once, and is announced in the task
contract. These controls validate that rule; they do not show that arbitrary
surprises, unknown transition laws or real systems are handled correctly.

## Verification and reproduction

```bash
python -m unittest discover -s tests -p test_discovery.py -v
python -m pomdp_bench.discovery_controls --validate studies/discovery-recovery-v1/controls.json
python -m pomdp_bench.discovery_controls --out artifacts/discovery-controls.json
python -m pomdp_bench.discovery_controls --validate artifacts/discovery-controls.json
```

Use the source checkout associated with this report. Existing output files are
not overwritten. The report validator rejects incomplete/duplicate/unplanned
matrix entries, changed source, declared-policy mismatches, observation edits,
post-terminal actions, type-changing grade edits and altered summaries.

The 17 focused tests cover the factorial rescue checks, exact witness budgets,
unrevealed/future-handle noninterference, label invariance, stale work, invalid
actions, explicit handover, step limits, report integrity and concurrent output
creation. A separate acceptance predicate reads only public history and agrees
with the state grader on all controls plus 250 deterministically perturbed
trajectories. This is independent implementation of the acceptance check, not an
independent team, exhaustive state-space proof or production security boundary.

Local Windows verification passed all **122 tests**, 24 existing diagnostic demo
trajectories and their replay, 156 immutable historical-file checks, released-data
verification and documentation checks. A second complete report reproduced the
published report byte for byte. CI also reproduces and validates this complete
prototype matrix on its Windows/Linux and Python 3.11/3.13 combinations.

## What was removed and what follows

Remove the presumed need for random seeds and model calls before checking a task
contract. Keep one active dependency, a single replacement and one acceptance
criterion. Reuse the existing JSON parsing/fingerprinting helpers, but do not
introduce a second durable collector or populate diagnostic metrics with fake
zeroes.

P3.1 is complete. P3.2 must justify useful structural variation and then integrate
with the existing evidence workflow. Depth, shared prerequisites or selective
invalidation must affect decisions, not just labels; each supported structure
needs a public-information solvability witness and budget. If this cannot be
shown, retain a small contract test and remove the broader family proposal.

No real endpoint was called. The failed all-four live integration gate from
[2.4](../direct-channel-validation-v2/README.md), P2 mechanism identification and
P4 external validity remain open and unchanged.
