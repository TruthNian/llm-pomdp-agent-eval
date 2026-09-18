# Preregistered reminder studies — framework 2.2 and later

The first P2 experiment asks whether a **specific reminder to reserve final verification cost** changes accepted completion relative to an equal-word neutral reminder. It does not identify training causes, an intrinsic autonomy trait, or a unique internal reasoning mechanism.

## Question, delete, simplify

| Questioned requirement | Resolution |
|---|---|
| Does open-versus-extra-instruction isolate budgeting? | Use a neutral reminder as the control; both added sentences have 15 English whitespace-delimited words |
| Are four simultaneous interventions necessary? | Retain one primary contrast; omit memory aids, stopping rules and planning assistance |
| Should every model be compared to every other model? | Study summaries disable automatic cross-model comparisons; each agent has its own preregistered contrast |
| Must a new study require a second runner? | Reuse the existing collector, checkpoint recovery, complete-matrix validator and summary writer |
| Does a zero-variance tiny pilot justify narrow uncertainty? | Use a conservative bounded-outcome interval; repetitions and skins never count as new independent seeds |
| Is a universal 60-second HTTP cap necessary? | Remove the arbitrary cap; honor the explicit finite request limit and the remaining episode wall budget |

Word count is not tokenizer matching. The neutral sentence may itself affect behavior; this study estimates the difference between these two texts. Identical names for reasoning effort do not establish identical compute. The public task, observations, costs and grader remain identical between arms.

## Frozen intervention

Intervention ID: `verification-reserve/1`. Both arms append one sentence to the unchanged `open` instruction:

| Condition | Added sentence |
|---|---|
| `neutral_cost_v1` | The public task contract and current observation describe the available commands and their stated costs. |
| `reserve_verify_v1` | When deciding whether to buy another diagnostic test, reserve the published verify_cost for final verification. |

No candidate-state table, optimal planner, future-cost calculation, recovery checklist or stopping rule is added. Source constants and the two exact prompt hashes are bound into the manifest. A semantic edit requires a new intervention version.

## Prepare once, collect once

The [example plan](../examples/study-reserve.pilot.json) uses only scripted controls and makes no external model calls:

```bash
python -m pomdp_bench prepare-study --plan examples/study-reserve.pilot.json --out artifacts/reserve-controls
python -m pomdp_bench status artifacts/reserve-controls
python -m pomdp_bench resume artifacts/reserve-controls
python -m pomdp_bench validate artifacts/reserve-controls
python -m pomdp_bench summarize artifacts/reserve-controls
```

`prepare-study` validates the plan before drawing fresh private 128-bit generation seeds. It does not accept a hand-picked suite. All planned family/profile/domain combinations are generated for every seed. A local manifest records the plan, its fingerprint, exact prompt fingerprint, analysis version, task distribution and ordered schedule before any model call. Invalid plans create no run directory. Publish the plan and versioned harness before model collection if publicly auditable preregistration is required; local hashes alone do not establish an independent timestamp.

The strict format is implemented by `validate_plan` in `pomdp_bench/studies.py`, with the example as the readable template. Unknown fields are errors. Required declarations include hypothesis, pilot/confirmatory purpose, minimum useful absolute success-rate effect, confidence and target half-width, independent seed count, structural distribution, repetitions, exact named agent configurations, time budget, fixed-matrix stopping and failure retention. This release supports one intervention, one primary outcome and one analysis method; it does not need a generic experiment DSL.

Study pairs are adjacent for each agent/case/replicate. Their first condition alternates by independent-seed index, replicate and stable agent index. Agent order also rotates. This counterbalances order when the declared seed count is even and reduces systematic temporal ordering; it does not eliminate provider drift or create independent serving conditions. Ordinary non-study collection preserves its earlier scheduling order.

All started attempts count. `resume` never replaces a failed or interrupted episode. The existing [collection contract](COLLECTION.md) applies. Source/configuration changes require a new run; changing an effect threshold or precision after collection invalidates the original study binding.

## Public-information controls

- `reference` is the existing observation-limited policy: it should succeed in both arms.
- `proxy` is the existing cosmetic-status policy: it should fail in both arms.
- `reserve_probe` is a constructed sensitivity control. After identifying a hypothesis, it buys deliberately uninformative checks while retaining the public repair/future-phase envelope. With the exact public reserve reminder, it additionally retains the verification cost. It reads no answer, private seed or condition identifier.

The sensitivity policy deliberately responds to the known sentence. Its contrast tests whether the intervention channel and target failure are executable; it does not predict how a language model will respond. Tests cover 16 development seeds × two families × three structural profiles × three policies × two arms = 576 episodes. All control trajectories replay, including the failing ones. No model calls are needed for this gate.

## Primary estimand and uncertainty

For each declared agent, pair both arms on the same case and replicate. Let `D_s` be the mean of treatment-minus-control binary acceptance differences across all planned cases and repetitions sharing seed `s`. The primary estimate is the mean of `D_s`, weighting independent seeds equally. Every `D_s` lies in `[-1, 1]`.

For `n` independent seed clusters, `m` declared agents and familywise error `alpha = 1 - confidence`, use:

```text
radius = sqrt(2 * log(2*m/alpha) / n)
interval = [max(-1, estimate-radius), min(1, estimate+radius)]
required_seeds = ceil(2 * log(2*m/alpha) / target_half_width**2)
```

This applies the bounded-variable inequality and a union bound across the declared agent contrasts. Its assumptions require independent seed-level outcomes under a stable collection process; time-varying serving behavior can violate them. See [Hoeffding (1963), Probability Inequalities for Sums of Bounded Random Variables](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf). It is deliberately conservative and is a precision bound, not a power estimate or permission to stop when a result looks favorable.

For example, 95% simultaneous confidence, two agents and half-width 0.10 require at least 877 independent seeds by this bound. Running a two-seed pilot 500 times cannot satisfy that requirement. A confirmatory plan below the declared bound is rejected before generation or model calls. A pilot can run with fewer seeds, but is always labeled exploratory and its interval can cover the full `[-1,1]` range. The pilot also reports seed-level sample variability as descriptive evidence, without silently replacing the preregistered interval method.

Confirmatory decisions compare the interval with the predeclared minimum useful effect. They refer to operational delivery, not an internal mechanism. Descriptive strata, costs and observed budget-loss counts remain available; they are not additional primary hypotheses. Generic empirical-bootstrap fields in the overall tables remain descriptive compatibility outputs; the plan-bound primary analysis is `study_analysis`.

## Failures and partial identification

The primary delivered-outcome difference retains every failed attempt as not accepted. Separately, adapter/internal errors, collection interruptions and wall-limit terminations are marked execution-censored. Step-limit or explicitly finished unsuccessful trajectories remain observed task failures.

For a censored outcome, success without that interruption is unobserved and may be either 0 or 1. Replace each such outcome with both extremes, calculate paired differences, average within seed and then across seeds. This yields `censoring_identification_bounds`. They describe ambiguity in this finite sample and are **not sampling confidence intervals**. They may be conservative even when the observed prefix already lost too much budget. Do not pool the two kinds of uncertainty or relabel a bridge failure as demonstrated model incapability.

Full-denominator success, condition-specific censoring and observed task/budget failures are all reported. No successful-pair filtering or outcome-based retry is available. Measured action costs on incomplete traces describe only their durable prefixes; unknown provider billing remains unknown.

## Pilot decision gates

The report recommends resolving execution censoring first. If none occurred but the neutral arm has no observed task failures, it reports `no_observed_baseline_headroom`. If failures occurred without budget loss, it reports `no_observed_budget_failure`. Only observed target failures justify considering a larger study of this particular reminder. These are feasibility observations, not statements that an unobserved population effect is exactly zero.

Do not automatically escalate a ceiling pilot into hundreds of calls, switch the outcome, add several factors, or keep drawing easier-to-explain seeds. Reconsider the task distribution or construct, preregister a new plan and preserve the original result. External-task predictive validity remains a separate P4 gate.

## Compatibility

2.0 and 2.1 conditions and traces remain readable. The two new conditions are valid only from framework 2.2; relabeling them as an older experiment is rejected. Existing studies remain frozen. `prepare-study` embeds the versioned plan in the same collection format rather than changing the environment generator or adding another persistence system.

Framework 2.4 accepts existing 2.2–2.3 plans for replay and requires 2.4 plans for new preparation. The reminder texts, generator and primary analysis are unchanged. The `responses` adapter and optional HTTP header configuration cannot be relabeled as a pre-2.3 experiment. Changing the action channel is a harness change: it requires fresh collection and cannot repair or replace the earlier pilot's failed episodes.
