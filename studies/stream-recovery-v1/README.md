# Destructive recovery and downstream dispatch

The first complete model screen ended in a business failure. The target remains a
useful, difficult POMDP incident. Runtime complexity and artifact controls do not
establish that difficulty.

The [evaluator contract](../../docs/STREAM_RECOVERY.md) distinguishes real executed
PostgreSQL/Kafka/Debezium behavior from the constructed commerce/carrier applications.
The agent receives sparse symptoms and a generic shell; evaluator notes, controls,
customer receipts and final grading remain outside its environment.

Four declared artifact controls completed from source `e88f16029e1510ccbefcc875a98253466d902e2f`,
using the same case, immutable image, collector and business checks. The final phase,
after a real restart, observed:

| Artifact control | Wrong order states | Missing dispatches | Duplicate dispatches | Delivered |
|---|---:|---:|---:|---|
| Untouched | 26 | 37 | 0 | No |
| Restore/merge tables, retain numeric receipt identity | 0 | 1 | 10 | No |
| Replay using new keys without preserving carrier receipts | 0 | 0 | 18 | No |
| Preserve receipts and reconcile recovered history | 0 | 0 | 0 | Yes |

Each retained 73 accepted orders and 55 release obligations in its final audit.
There were no observer, command-receipt or retry-probe errors. The three recovery
controls each incurred four refused customer commands during maintenance, which remain
in the evidence. Real-time traffic is not asserted to be a byte-identical schedule.

The table-only control dispatched the same event
`5267bbc8-ffba-54d3-94e4-c9a7c66c80a5` under both `outbox:41` and `outbox:135`,
creating two independently persisted carrier bookings. Blind replay similarly
repeated all eighteen previously committed consignments. The complete control
uses ordinary backup/WAL and carrier evidence to preserve those effects.

These are known-solution artifact experiments, not model results or blind
observation-only discovery policies. They establish an executable feasible path
and actual consequences, not high difficulty.

## Complete Sol attempt and attribution limit

The declared `gpt-5.6-sol` max route handed over after **29/200 actions**, in
1937.463355 seconds including setup and independent terminal observation. Both
terminal phases found **12 missing/wrong order states and 9 missing dispatches**.
The final phase covered 103 accepted orders and 85 release obligations. There were
no duplicate, unexpected or changed bookings; no observer, request-retry, protocol
or adapter errors. Maintenance caused 226 refused customer commands. All are retained.

The agent restored the 31 divergent events present in the old Kafka topic, repaired
event-UUID deduplication and migrated the eighteen existing dispatch receipts. It
created a fresh CDC source and verified agreement among the records it had recovered.
It did not restore the 28 later old-branch commands absent from Kafka. Its final
checks compared local orders, requests, outbox and carrier records with each other;
that closed set omitted twelve orders and nine release obligations. Backup/WAL
recovery was accessible through ordinary operational files, as the positive control
demonstrated. This is an observed recovery-completeness failure, not a timeout score.

**The preregistered ceiling interpretation needs qualification.** Review during
collection found that `responses_tools` issues a fresh request containing the full
public-history JSON for every action. It does not carry native assistant/function
items or encrypted reasoning state forward. The [official function-calling guide](https://developers.openai.com/api/docs/guides/function-calling)
requires reasoning items to accompany tool outputs for reasoning models. This
attempt measures the declared stateless history policy, not an unrestricted native
continuous agent. The effect of that limitation has not been measured here.

No request, environment or budget was changed during the attempt. Preserve this
result, execute a fresh data-restoration counterfactual, and separately test the
same incident with continuous native dialogue before claiming a strong-agent ceiling
or proceeding to a model comparison. Do not attribute the repeated status checks
or the omission solely to the model or solely to the adapter without that comparison.

The [complete model trajectory](trajectories.html), [control trajectories](controls.html)
and machine-readable evidence can be rechecked with `python studies/stream-recovery-v1/verify.py`.

Run the frozen controls with `python -m tools.qualify_stream <unused-output-directory>`
after configuring `POMDP_STREAM_CONFIG` and building the image with
`python -m tools.build_stream <local-config.json>`. Preparation refuses a dirty tree.
The [frozen model plan](plan.json) declares one native Sol max attempt, 200 actions,
600 seconds per request, 10800 seconds for the complete episode and a 16 MB wire
response limit. Only public handover, operational outputs and its own action history
enter model requests. No intervention or retry is permitted. Clean delivery rejects
the candidate's high-difficulty claim. Business failure requires causal attribution
and fresh counterfactual execution before a separately registered GLM follow-up.

All eventual outcomes will be retained separately from development attempts.
Historical takeover studies remain unchanged.
