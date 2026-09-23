# Continuous native recovery screen

**The complete Sol max attempt delivered in 31/200 actions. Reject this candidate
as continuous-agent high-difficulty evidence, as preregistered.** Retain the incident
and all earlier failures as regression and measurement anchors.

The [plan](plan.json) keeps the same scenario, immutable image, 200-action budget,
600-second request timeout, 10800-second episode limit and 16 MB wire limit as
the completed [stateless attempt](../stream-recovery-v1/README.md).

The newly versioned adapter retains the native assistant/function dialogue and
encrypted reasoning state. It removes an identified measurement limitation without
adding incident information, guidance, tools or evaluator feedback. The environment
source hashes and image match the earlier four qualification controls. No control
result or recovery script enters the model's observation.

## Observed business outcome

| Independent phase | Accepted orders | Accepted releases | Order errors | Missing / duplicate / wrong / unexpected bookings |
|---|---:|---:|---:|---|
| Before restart | 105 | 89 | 0 | 0 / 0 / 0 / 0 |
| After actual restart | 111 | 93 | 0 | 0 / 0 / 0 / 0 |

The attempt voluntarily handed over after thirty terminal calls and one finish.
Recorded elapsed time was 1338.958090 seconds, including environment setup and
terminal acceptance. There were no adapter, observer, receipt, retry or new-command
errors. Four terminal calls returned nonzero status; additional unsuccessful
subcommands remain visible inside otherwise successful shell calls. No attempt was
retried or replaced. Maintenance refused 128 customer command requests; that cost is
retained, not erased by eventual delivery.

All 31 requests reported usage: 6,210,060 aggregate input tokens, 30,625 output
tokens and 14,132 reasoning tokens. Input counts include repeated context, not
6.2 million unique words or independent observations. The adapter retained 47 native
reasoning items across the responses. Local route and authentication bytes were
unchanged throughout collection.

## What the complete trajectory shows

Actions 1–13 investigated the deployed application, database roles, Kafka, carrier
receipts, ordinary logs and backups. After correcting its log parser, the model
compared acknowledged requests against current data and found 59 missing events;
Kafka contained only 31 of those events. It found the physical backup and archived
WAL without evaluator guidance.

Action 14 restored timeline 1 into a separate read-only PostgreSQL instance.
Actions 15–17 reconciled recovered and current branches. A Python KeyError rolled
back the first merge transaction; the next action corrected it. The committed
merge retained 168 requests/events and 75 orders. Unlike the earlier attempt,
this restored the old branch beyond Kafka's retained prefix.

Actions 18–23 checked existing carrier effects before resuming dispatch. The model
preserved old-branch outbox IDs 1–79 and reassigned current-only IDs to 80–168,
retaining the carrier's existing idempotency identities. It created a fresh
connector namespace against the surviving primary, retained the original topic
and consumer, and reconciled all 61 then-accepted releases before reopening the
API. Rewriting the consumer was not required for this valid recovery path.

Actions 24–30 checked ongoing customer work, an old-branch request retry, order
revision histories, carrier contents, local receipts and replication. Its final
reconciliation script initially hit a float/Decimal error and was corrected.
Its optional physical check did not run because the amcheck extension was absent;
the trace records that warning, not a claimed physical verification pass. Action
31 handed over. Only then did the evaluator run its own workloads and restart;
the private acceptance result was never model feedback.

## Decision and limits

Apply the rejection rule: stop expanding this miniature order-service candidate
as the frontier mainline. Real PostgreSQL recovery, Kafka and irreversible local
carrier effects did not prevent complete delivery by this continuous configuration.
This is a design decision supported by the observed solution, not an estimate that
all agents or all incidents are easy.

The [earlier stateless failure](../stream-recovery-v1/README.md) remains a genuine
business failure under its declared policy. The [matched artifact experiment](../stream-recovery-counterfactual-v1/README.md)
isolates missing history as its business mechanism. These two unpaired real-time
model attempts do not identify the causal effect of conversation continuity:
their policies and accepted background workloads differed. They are not pooled
into a model ranking. No GLM attempt was run in this study.

Acceptance covers the versioned workload, every accepted order state and its
required shipment, with one evaluator-selected exact/conflicting request retry.
It does not exhaustively retry every historical command, establish resilience to
another future failover, or demonstrate production predictive validity. The model
also checked an old-branch retry on its own. Those scopes remain distinct.

Read the [complete trajectory](trajectories.html) and [machine-readable evidence](model-evidence.json).
Run `python studies/stream-recovery-continuous-v1/verify.py` to regrade business
observations and reconstruct all public request projections.

## Protocol diagnostics and public audit

Two development protocol diagnostics are retained separately. Each made two requests
without executing an environment or scoring a task. The first completed exec/finish
but emitted zero reasoning items, leaving the reasoning-continuity assertion unexercised
and recorded as a failed diagnostic assertion. The second used a small combinatorial
prompt to exercise reasoning; native continuation succeeded with encrypted state.
Mathematical correctness was not scored. Both original records remain unchanged.

Public auditing reconstructs the request projection from recorded assistant/function
items and tool observations, with opaque reasoning represented only by hashes. It
does not claim to reproduce encrypted request bytes. See the [adapter contract](../../docs/MODEL_ADAPTERS.md).

The two diagnostic sequences remain outside the incident score. Their original
records are retained unchanged; neither is evidence of task difficulty.
