# Reconciliation repair — development qualification

The operator now repairs executable SQL components, deploys them and recovers
materialized business output. The two constructed contracts cover capture snapshots
and correctable postings. [Task and architecture](../../docs/RECONCILIATION_REPAIR.md).

**Decision: useful repair capability demonstrated; high difficulty remains unproven.**
The two scheduled live attempts were interrupted by transport failures. Their
zero accepted deliveries cannot be interpreted as cognitive task failures. The
first attempt had already fixed historical reconciliation; its unchanged SQL also
passes a separately labeled post-hoc probe check with scripted completion.

## Frozen collection

Source: `ce6cab7bac22f91ee44cf0c132a7bc6bd2ab63bf`, framework 2.11.0,
`reconciliation-repair/1`. [Plan](plan.json) pins the complete two-case suite,
requested `gpt-5.6-sol` with max reasoning, 80 actions, 600 seconds/request and
3600 seconds/episode. One attempt per contract, no retries or replacement.
GLM was not scheduled; this is a strong-route ceiling screen, not a model comparison.

| Contract | Actual actions / requests | Elapsed | Retained outcome |
|---|---:|---:|---|
| Capture snapshots | 14 / 15 | 125.006 s | Request 15: `Endpoint transport failed`; no handover |
| Posting corrections | 0 / 1 | 2.041 s | First request: `Endpoint transport failed`; no business runtime created |

[Readable full trajectories](trajectories.html) · [Original model records](model-evidence.json).
Both failed attempts remain in the matrix. No extra model call was used to replace
either result. Failure cause was not identifiable from sanitized transport evidence.
A later TCP probe found the local route port open; this does not establish upstream
health or explain the earlier failures. No claim about model cognition follows.

In the first attempt, steps 9–10 patched normalize and resolve; steps 11–13 tested,
deployed and refreshed. At step 13 all four historical positions and all totals
matched independent provider truth. Step 14 submitted the first new workload batch;
then the connection failed before a second batch, final refresh, verification and
handover. This is partial observed delivery, not accepted model completion.

All 14 returned model labels matched the requested route label. The two failed
requests have unknown reported identity. Labels do not attest model weights.
The first attempt has usage for 14/15 requests: known subtotals 31,388 input,
2,814 output and 2,378 reasoning tokens. Reasoning may be included in output;
do not add it again. The second attempt has no usage-bearing request. Complete
usage totals for both attempts are **unknown**, not zero.

The before/after configuration control passed separately for `config.toml`,
`auth.json` and `native-session-consent.json` (including absence as a byte state).
This is a start/end equality check, not proof of continuous invariance. It does
not identify a transport failure's cause or repair it. The earlier external
settlement study's failed configuration control remains unchanged and disclosed.

## Predeclared component controls

All thirteen public-contract policy trajectories were executed and freshly
re-executed, comparing every action and response. The source is
[controls.py](controls.py) plus the package's `reconciliation_control.py`.
The policies implement the published contracts; they read public history only,
but are hand-written feasibility controls, not general source-repair solvers.

| Policy | Capture snapshots | Posting corrections |
|---|---|---|
| Complete contract implementation | Accepted, 27 actions | Accepted, 27 actions |
| Normalize only | Rejected | Rejected |
| Same fixed resolver patch | Rejected | Rejected |
| Global object identity | Rejected | Rejected |
| Correct code without refreshing stored output | Rejected | Rejected |
| Ignore generation, use revision only | Rejected | Accepted: postings have no generation reset |
| Discard negative/zero rows in totals | Not scheduled | Rejected despite correct individual positions |

[Readable control trajectories](controls.html) · [Complete control evidence](control-evidence.json).
The unscheduled cell has no observed outcome. Errors count missing plus surplus
rows in a multiset comparison, not distinct wrong objects. These results qualify
mechanism sensitivity and rule out these partial recipes; they do not establish
that a strong general model finds the task difficult. Script wall times were not
measured, and their record field of zero is not an empirical timing result.

## Separate post-hoc check of the observed model patch

After retaining the failed attempts, [check_patch.py](check_patch.py) re-executed
the exact 14-action model prefix without changing its SQL. A disclosed 13-action
scripted suffix submitted the second batch, inspected/waited for delayed events,
refreshed, verified and handed over. The resulting twelve positions and totals
passed, including both new batches. [Full separate artifact](patch-check.json).

This check was **not preregistered**. It qualifies the existing patch on the
fixture's probe workload; it is neither a resumed live episode nor a model success.
The original model result stays rejected. It also supports a cautious engineering
judgment: the observed snapshot repair itself did not challenge this route visibly.
There is no corresponding model patch or competence evidence for posting corrections.

## Reproduction and next gate

Model and control records use the same frozen package hashes. Recorded replay
checks complete observations and grades without executing SQL. Fresh reconstruction
of all applied live actions matched exactly; the zero-action attempt has only a
newly constructed initial-state illustration, not an observed final database.
The post-hoc artifact was also freshly executed and replayed separately.
[execution.json](execution.json) pins source and published file hashes.

```console
python studies/reconciliation-repair-v1/evidence.py verify
python studies/reconciliation-repair-v1/controls.py artifacts/reconciliation-controls.json
python -m pomdp_bench recheck artifacts/reconciliation-models-v1
```

The third command needs the original private collection and frozen source. It
executes local services/SQL but never requests another model response. The model
launcher is [collect_local_study.py](../../tools/collect_local_study.py); its
`prepare` and `collect` phases enforce the plan/suite/source boundary and retain
failures. Historical launchers/evidence were not rewritten.

Retain this as a component-repair regression anchor. Do not expand the same
fixtures through more rows or syntax constraints. Difficulty calibration still
needs fresh, separately frozen uninterrupted full interactions. The next substantive
candidate should connect evidence-driven component repair to consequential recovery
in the existing external-state environment, with faults grounded in independently
sourced incidents. Query tools stay available; original anchors remain fixed.
