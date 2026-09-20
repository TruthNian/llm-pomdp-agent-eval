# Experimental depth and explicit solver pilot

The question is whether deeper coverage tasks primarily demand unaided
combination search, and what remains when that search is an available action.
The [frozen plan](plan.json) declares four attempts on one public development seed:
depth24 × two model configurations × open/solver_assisted. It uses the shared
collector, with no replacement attempts. This document initially records the
plan; execution evidence will be added after the complete matrix is retained.

## What changed and why

- **Question:** is larger combinatorial search a durable test of general agents
  when useful tools are available? A fixed script with an exact public-data
  solver already succeeds on the 24 qualified cases. Model difficulty remains
  an empirical question; tool-assisted workflow is a narrower construct.
- **Delete:** do not promote the candidate with ten reference-limit failures,
  pool direct and assisted scores, infer FLOPs from search states, or introduce
  a second collector. Prior failures and unexecuted controls remain published.
- **Simplify:** register only the two qualified graph streams, with explicit
  experimental metadata. Add one model-chosen JSON action using the same pure
  search and deterministic replay. A plan is a suggestion, not completed work.

## Conditions and acceptance

Both conditions have identical goals, revealed information rules, inspection/
work budgets, step horizon and terminal predicate. Only solver_assisted exposes
the explicit solve action and its allowance: two calls, one million visited
search states per call. It cannot read hidden rows or future matrices, execute
builds, repair a stale plan or certify PASS. The model must probe, request help
when useful, build, respond to change, re-probe, rebuild, verify and finish.

The solver consumes additional compute. State counts are deterministic algorithm
effort, not tokens, FLOPs or a compute-matched contrast. Search exhaustion is
unknown, and absence of a plan in revealed rows is not global infeasibility.

All models use high reasoning, a 600-second request deadline, a 1,800-second
episode deadline and an explicit 16,000,000-byte response-body allowance.
No optional output token cap is sent. Provider tools remain empty; solve is an
environment JSON action. Serving checkpoints and internal proxy behavior are
not attested by a requested route label.

## Boundaries set before requests

- Exactly four attempts in the declared serial order; no time/order balancing.
- One public seed reused from offline qualification, not a private evaluation.
- depth18 is implemented and tested offline but receives no model call here.
- Reserve 120/5/360 and 120/3/240 without generating or evaluating them in this
  pilot. These are parameter combinations, not independent structural families.
- Keep all earlier pilots under their original settings and source versions.
- A transport/deadline failure leaves capability censored. Uniform successes or
  failures cannot establish useful discrimination. No ranking, training-cause,
  population saturation, contamination or real-work prediction claim is licensed.

## Reproduction

The [registered offline control evidence](control-evidence.json) retains all 48
episodes on public seeds 0–11, collected at clean commit
`2715f1330456f439c31d71f00f8867120a813635`. Every case regenerates and every
trace replays; the two control runs' source hashes match this implementation.

| Profile | Public cases | Open exact reference | Explicit solver consumer |
|---|---:|---:|---:|
| depth18 | 12 | 12/12, 7 actions each | 12/12, 9 actions and 2 solver calls each |
| depth24 | 12 | 12/12, 7 actions each | 12/12, 9 actions and 2 solver calls each |

Maximum total visited solver states per episode were 9,725 and 67,824
respectively. They measure this search algorithm's effort on these cases.
Open references use their own computation, which is not a zero-compute model
measurement. Model usage is inapplicable to both scripted controls.

Tests additionally bind the renamed cases, selected reference plans and search
counts to the previous qualification's frozen hashes. All 160 unit tests and all
four Windows/Linux Python 3.11/3.13 CI jobs passed at this source. Frozen history
(156 files), the prior 192 coverage controls, both four-attempt model pilots and
the 60 discovery controls remain valid. An initial standalone control-script
import failure was fixed before any model request; it produced no control
episodes and did not replace an outcome.

```bash
python studies/coverage-depth-v1/controls.py artifacts/depth-controls
```

Use the source revision recorded in the eventual evidence. The launcher reuses
the prior explicitly authorized installed route, checks plan/manifest hashes,
and keeps login/router/consent files unchanged. Raw generated cases and
credentials stay outside Git. Preparation makes no requests.

```bash
python studies/coverage-depth-v1/launcher.py prepare artifacts/coverage-depth-live-v1
python studies/coverage-depth-v1/launcher.py collect artifacts/coverage-depth-live-v1
python -m pomdp_bench validate artifacts/coverage-depth-live-v1
python tools/export_coverage_evidence.py artifacts/coverage-depth-live-v1 artifacts/depth-evidence.json
```

Public outcome exports contain configuration, condition, retained grades,
sanitized failures, usage availability and hashes reconstructed from each public
model request. They omit raw provider bodies, private future matrices and secrets.
