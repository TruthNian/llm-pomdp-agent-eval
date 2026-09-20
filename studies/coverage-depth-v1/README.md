# Experimental depth and explicit solver pilot

The question is whether deeper coverage tasks primarily demand unaided
combination search, and what remains when that search is an available action.
The [frozen plan](plan.json) declares four attempts on one public development seed:
depth24 × two model configurations × open/solver_assisted. It uses the shared
collector, with no replacement attempts. All four attempts are now retained in
the [live evidence](live-evidence.json), including both request-deadline failures.

## Complete public-pilot results

The source and plan were published before model requests, at clean preparation
commit `2715f1330456f439c31d71f00f8867120a813635`. The run's core source hashes
still matched the export checkout. One public depth24 case was used throughout.

| Configuration | Condition | Accepted | Actions | Episode seconds | Complete input / output tokens |
|---|---|---|---:|---:|---|
| gpt-5.6-sol, high | open | No: next request after probe timed out | 1 | 603.146478 | Unknown |
| custom/z-ai/glm-5.3, high | open | No: next request after probe timed out | 1 | 602.008850 | Unknown |
| gpt-5.6-sol, high | solver_assisted | Yes | 9 | 43.971286 | 405,648 / 761 |
| custom/z-ai/glm-5.3, high | solver_assisted | Yes | 9 | 144.021659 | 468,256 / 10,354 |

The directly observed acceptance difference is +1 within each configuration on
this one case. Both open attempts stopped after probing 288 rows, with no builds,
following the fixed 600-second request deadline. The observations do not identify
whether additional time would produce a valid plan or distinguish model search
effort from serving delay. Keep these as failed deliveries with censored
capability evidence, not proof of cognitive inability or a causal solver rescue.

Both assisted runs chose exactly
`probe → solve → build → verify → probe → solve → build → verify → finish`.
They used 47 builds, 576 inspections and all 625 operational points, completed
96 goals, recovered once and verified the current state. Each made two solver
calls totaling 49,441 visited states; neither exhausted the search allowance.
This matches the fixed tool-consumer control on this case. It does not establish
population saturation or discriminate these two model configurations.

All four trajectories replay, and all 22 request fingerprints reconstruct from
their public contract, observation and action history. Twenty requests provide
complete usage. The failed request in each open run has unknown usage, so those
episode totals remain null; the export retains the available partial counters.
Assisted reported reasoning tokens are 415 for Sol and 9,951 for GLM, included
within the reported output counts rather than added again.

The response label matches the requested Sol name on completed requests; GLM's
reported label differs from the configured alias on all ten completed requests.
Neither label comparison is checkpoint attestation. There were no extra probes
to identify a backend, no retries, and no new evaluation seeds. The launcher's
before/after check found login, router configuration and consent bytes unchanged.
The 16 MB allowance was declared uniformly; this study does not measure the
actual wire-byte count or independently validate every provider route.

## Decision after the pilot

1. **Narrow the claim.** Retain these profiles as experimental combination-search
   and tool-use controls. The workflow admits a fixed policy when a useful exact
   solver is available. Neither the two open timeouts nor the two assisted
   successes pass the private-seed discrimination gate. Do not enlarge the
   catalogue or time allowance merely to turn these outcomes into a ranking.
2. **Delete measurable representation waste next.** The assisted input totals
   above are provider reports, not fabricated zero-cost tool use. Code inspection
   shows the current request repeats entire observation snapshots in history,
   including unchanged catalogues. A future version should test a losslessly
   reconstructable public-history encoding before spending on a larger matrix.
   No compressed request was sent here; no token saving or model-equivalence
   result has yet been measured.
3. **Make information choices consequential.** Current all-row probing is
   affordable and the change is announced. A next minimal prototype should
   require choosing which information to acquire under constraints, while useful
   solvers remain available. Require a public-information witness, competent
   tool-equipped baselines and matched rescue ablations before model collection.
   Untuned parameter combinations remain reserved, not automatically promoted.

This is a development decision from a small public pilot. No claim about
parameter scale, post-training causes, model population ranking or real-work
predictive validity follows.

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

Use the source revision recorded in the evidence. The launcher reuses
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
