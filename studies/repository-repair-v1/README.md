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

**First execution passed**, using clean source commit
`136e0c5885029aff3306237c9cf93c55907ee057` in
[CI run 35494806761](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35494806761).
All six attempted controls remain in [control-evidence.json](control-evidence.json).
[execution.json](execution.json) binds its byte hash, workflow, image ID and
image repository digest. There were 8 original container calls, 8 fresh recheck
calls, and zero model calls. All six recorded traces also validated locally
after downloading the full CI artifact.

| Control | Observed behavior | Delivery |
|---|---|---|
| unchanged | Reproduction failed; 54/118 full checks matched | Rejected |
| example-only | Reproduction passed; 50/118 full checks matched | Rejected |
| upstream-artifact | 118/118 matched | Accepted |
| unverified-later-edit | 118/118 before later edit; PASS expired | Rejected |
| test-tampering | Test edit rejected; 54/118 matched | Rejected |
| exit-zero | Empty behavior output; invalid_response | Rejected |

All fresh rechecks agreed with original observations and grades. Recorded
values and patches can be audited locally without Docker:

```bash
python studies/repository-repair-v1/verify.py
```

For fresh execution, run the control command in the task contract using the
recorded image. A new run has its own directory and provenance; it does not
replace this first execution. These results validate the declared repair
acceptance loop. They do not measure model performance or frontier difficulty.
