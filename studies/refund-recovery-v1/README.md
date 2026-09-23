# Refund recovery: candidate rejected as high-difficulty evidence

**Sol max delivered in 39/100 actions and 636.495 seconds. This iteration did not meet the high-difficulty objective.**

All external orders, eight approved refund allocations, local books and individual
refund projections passed. There were no excess refunds, invalid actions, adapter
errors or failed verification attempts. Two new batches completed. Every action
response and the final databases matched fresh execution. This is one model attempt
on one constructed scenario; it is not a general model ranking.

The [plan](plan.json), environment and budgets were frozen at
`2ac6827cc904d7edcc0f68ad826de1b44feaf984` before collection. The model received no
mid-run human intervention, reference policy, grader source or private manifest.
100 actions, 600 seconds/request, 3600 seconds/episode and max reasoning were not
changed after observing behavior. All 39 request labels matched the requested route;
labels do not certify weights. All requests included usage: 232,636 input tokens,
17,511 output tokens, of which 16,445 were reported reasoning tokens. Do not add
reasoning tokens again. Config, authentication and consent bytes were unchanged.

## What happened

| Steps | Observed behavior |
|---|---|
| 1–12 | Inspected contracts/source, kept the worker paused, retrieved authoritative provider state and queried intents/callbacks |
| 13–17 | Patched all three components, tested and deployed; no patch retry |
| 18–22 | Rebuilt local state, funded the reserve, rekeyed the terminal failed refund and enabled processing |
| 23–28 | Created and funded two fresh batches, inspecting actual provider operations |
| 29–37 | Checked settlement/callback progress, refreshed projection and inspected final books |
| 38–39 | First verification passed; explicit handover |

The original broken mechanisms have real consequences. Eight scripted controls
were freshly executed and reexecuted, with all preregistered outcomes retained:

| Public-history control | Delivered | Actual consequence |
|---|---|---|
| Complete reference | Yes, 43 steps | All business predicates satisfied |
| New request key on each attempt | No | 150 cents excess refunded; two orders incorrect |
| Updated callbacks only | No | One refund projection missing |
| Charge amount as refund amount | No | Nine refund projections and five books incorrect |
| Group partial refunds by order | No | Four refund projections and three books incorrect |
| Reuse terminal failed key | No | One external obligation not delivered |
| Never refresh | No | Five books incorrect, projection stale |
| Swap the two new partial-refund amounts | No | Order totals and books correct, four intent allocations wrong |

These controls establish execution/grading sensitivity. They do not establish
model difficulty. Source reports, independent upstream mechanisms and constructed
financial timings are explicitly separated in the [contract](../../docs/REFUND_RECOVERY.md).
No upstream application or historical production incident was executed here.

## Decision and design diagnosis

Apply the stopping rule: **stop extending miniature SQL fixtures as the frontier
mainline. Retain this version as regression evidence.** More fixture variants,
longer trajectories or additional unit tests would not reverse this result.

The trajectory supports a design diagnosis: the component locations and intended
semantics are directly documented, the entire candidate source is three short SQL
rules, and a full provider read resolves the initial commitment uncertainty.
The model corrected all rules on the first try and then executed ordinary recovery.
Irreversibility makes mistakes consequential, but does not make the correct decision
hard when state and causality are readily resolved. This diagnosis is an inference
from the task and behavior, not a causal claim established by an ablation study.

The next frontier candidate must start from an independently sourced complex task
and preserve its investigation/repair/recovery burden. Reuse existing collection and
isolated execution. Screen full strong-model interactions before expanding a new
family. A source citation, a one-shot patch failure or a provider outage is not the
required evidence. No high-difficulty achievement or completion date is claimed.

- [Complete live trajectory](trajectories.html) and [sanitized evidence](model-evidence.json)
- [All control trajectories](controls.html) and [control evidence](control-evidence.json)
- [Execution and byte bindings](execution.json)

```bash
python tools/service_study.py verify studies/refund-recovery-v1
```

Verification regrades recorded behavior without calling a model or executing SQL.
Fresh reconstruction was separately performed during evidence export. The eight
controls were collected by the frozen [control script](controls.py). Reports and
export tooling were added after collection began; candidate/runtime/collector
source remained unchanged, and published tooling is byte-bound here.
