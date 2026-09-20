# Repository repair v1 — fixed acceptance controls

Purpose: turn a real source snapshot and a reported defect into an executable,
inspectable patch-delivery task. This validates the environment and behavioral
acceptance contract; it contains no model calls or model-difficulty claim.

The [task contract](../../docs/REPOSITORY_REPAIR.md) pins pypa/packaging issue
1204 and pre-fix source. The upstream patch from PR 1206 is an artifact control,
kept outside the agent workspace.

## Matrix fixed before execution

[controls.py](controls.py) freezes one task, six action sequences, 40 steps,
8 checks and 300 wall seconds per sequence. No outcome-dependent replacement.

| Control | Required outcome |
|---|---|
| unchanged | Reported reproduction and full verification fail |
| example-only | Reproduction passes, full verification fails |
| upstream-artifact | Full verification passes; current patch is accepted |
| unverified-later-edit | Earlier PASS expires; delivery fails |
| test-tampering | Test edit rejected; unchanged source fails |
| exit-zero | Process exit 0 without behavioral values fails |

Every originally attempted execution is retained. Recorded-behavior replay checks
consistency. A second set of fresh containers re-executes the recorded checks;
discrepancies are recorded separately and fail the gate without replacing scores.
The gate requires all six rows, the specified separation, and no recheck error.

The CI workflow records a resolved immutable Python image ID and repository
digest. It uploads the full matrix even when a gate fails. Local unit tests use
explicit response fixtures and do not count as real candidate execution.

## Execution record

Implementation and matrix are prepared; actual container evidence will be added
after the first CI execution. No code-execution or model outcome is claimed yet.
