# Format-feedback follow-up

One additional complete GLM-route episode is fixed by [plan.json](plan.json),
under framework 2.9.1. It follows the preserved
[original incident collection](../settlement-incident-v1/README.md), in which the
old parser terminated GLM after 13 applied actions. This is an integration
validation, not a fresh model comparison or a replacement of that failure.

Completed malformed assistant action text now consumes a rejected environment
step and exposes format feedback on the next turn. No action is guessed; no
transport retry occurs. Envelope and transport failures remain terminal.
Local wire tests exercise both recovery to successful business delivery and
persistent invalid output exhausting the finite action budget.

The environment, public task, reasoning effort, action budget and request/wall
limits are unchanged. Only this episode's source/version and adapter recovery
semantics differ.

## Result: complete delivery, with format recovery

[Readable full trajectory](trajectories.html) · [original records and reconstructed
database](model-evidence.json) · [source and file identities](execution.json).

The requested `custom/z-ai/glm-5.3` route completed **26 of 60 actions** and handed
over after a passing verification. All **33 accepted orders** reconciled; no outbox
messages remained unresolved, and processing/monitoring stayed enabled. Every
action matched fresh HTTP/SQLite execution from the frozen collection source
`f4f609f1a427485c469bcd8a33377c9544103f36` before the later clock fix was merged.

- Steps 1–3 used the wrong field name and received ordinary environment feedback.
- Steps 10 and 15 returned completed malformed action text. Both consumed a rejected
  turn, preserved a text hash and usage, and were followed by further model actions.
  `invalid_model_output` is the adapter's rejection marker, not original model text.
- The route inspected operational/ledger information, configured and restarted the
  worker, rebuilt six historical messages, then appended five correcting credits.
- After reconciliation, it submitted four extra workload orders and queried the
  resulting state. Step 25's formal verification submitted four more; step 26 handed over.

This exercised live recovery, not just a fixture. It did not retry a failed request
or replace the original v1 parser failure. All three model attempts across both
collections remain published, with their different adapter versions.

Reported input/output tokens: **102,636 / 93,363**; reported reasoning tokens:
92,323 (already part of output, not additional). Total episode wall time:
**1,454.48 seconds**. Actual service HTTP requests: 75. Observed exposure sums:
69,981 excess-debit cent·ticks and 112 unsettled-message ticks. These sums end at
termination, include pre-existing incident damage, and are not unconditional model
rankings. The extra workload also differs from Sol's original trajectory.

All 26 reported model labels differed from the requested route string; these data
describe that configured route and do not attest the underlying model weights.
Local configuration/authentication files remained byte-for-byte unchanged.

## Decision

Retain this scenario as a complete-workflow regression anchor. Its two delivered
strong-route trajectories do **not** fulfill the project's high-difficulty target.
Format errors must not become the source of claimed frontier discrimination.
Implement the [external settlement decision problem](../../docs/EXTERNAL_SETTLEMENT.md)
next, preserving the current environment and all recorded outcomes.

Framework 2.9.2 subsequently corrects arrivals after rejected final commands and
clarifies the verification batch description. This episode used neither malformed
`verify` nor malformed `finish`; nevertheless it remains a 2.9.1 measurement and
must not be silently relabeled. Fresh reproduction of its exact public text needs
the frozen collection source; recorded replay works on the corrected framework.

```bash
python studies/settlement-incident-v1/verify.py --study studies/settlement-incident-v2
```
