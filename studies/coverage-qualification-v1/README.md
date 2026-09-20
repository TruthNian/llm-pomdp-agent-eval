# Bounded reference and recovery qualification

Status: **the fixed matrix is complete: 252 planned rows, 232 executed/replayed,
20 explicitly unexecuted because their initial-reference prerequisite was unavailable.**
Two candidate structures pass this offline gate; the third does not.
No model requests are included. All candidates remain outside the scored generator and CLI.

## Question, delete, simplify

The [earlier screen](../coverage-search-v1/README.md) exceeded a 5,000-state
development limit on several structures. That was not proof of intrinsic hardness,
model discrimination, or practical inability to solve the instances.

Under a tight work allowance, the goal count equals operation width times remaining
builds. Every chosen operation must therefore cover a full-width, disjoint set of
missing goals. The 2.5.3 reference uses bitsets for goal-to-row membership and row
conflicts, eliminating repeated row-list reconstruction at each search state.
It preserves the least-supported-goal choice, goal/operation tie breaking,
memoized failed states and state-count budget. The existing general cover search
still handles slack and overlapping solutions. These are complementary paths,
not a change to task semantics or a new claim of algorithmic hardness.

Experimental sampling now passes explicit dimensions to a shared internal sampler.
It no longer mutates the released scale table or generator version in its process.
Unsupported experimental cases are still rejected by ordinary suite validation.

## Paired search comparison

[All 180 paired calls](search-comparison.json) reproduce the previous public
catalogues. Both the immutable 2.5.2 solver and the optimized solver match every
published outcome, completed state count and solution fingerprint. Exhaustion
remains exhaustion at the same limit.

On this one Windows/Python 3.13 desktop run, total solver time was **48.300365
seconds before and 1.868399 seconds after** (25.85 times faster). Order alternated
within pairs. This is a machine-dependent measurement over these inputs, not a
universal speed guarantee, increased task difficulty or a model-compute estimate.

The [comparison script](compare_search.py) reads the exact baseline source from
Git commit `675d452db7739aa39a6d42353470292842f9e530` and verifies its hash against
the original published evidence. A clone containing that commit is required.

```bash
python studies/coverage-qualification-v1/compare_search.py --out artifacts/search-comparison.json
```

## Fixed candidate checks

The [plan](plan.json) specifies 3 candidate shapes × 12 public seeds × 7 controls:
**36 instances and 252 planned control rows**. The reference receives up to
1,000,000 states per decision, the existing released reference allowance.
The earlier 5,000-state results remain unchanged. Initial and recovery searches
are recorded separately; an exhausted reference is never labeled infeasible.

The controls are a full reference, greedy and rarest-goal heuristics, both
heuristics with relaxed work allowances, a policy that does not recover, and that
same policy with external change removed. Budget and recovery ablations preserve
the corresponding sampled catalogues. Non-revising controls reuse the reference
plan obtained from the same public initial catalogue and work allowance. This
isolates recovery necessity; it is not an independent solver-speed measurement.
If the initial plan is unavailable, those two controls remain explicitly
unexecuted. They are not assigned invented outcomes or silently removed.

Every executed control is replayed through a fresh environment before export.
Reference plans additionally pass an independent set-union check over public
rows. Published rows contain grades, search effort and public-trace fingerprints;
raw provider data and credentials do not exist in this offline experiment.

The plan was written before these checks ran but was not externally preregistered.
The output records the actual Git base, dirty-checkout flag, plan fingerprint and
source hashes. These are adaptive public development cases, not private or
held-out evaluation.

```bash
python studies/coverage-qualification-v1/qualify.py --out artifacts/candidate-qualification.json
```

No collector, retry service or model adapter is added. This offline check uses
the existing environment and policies; it does not register candidate scales.

## Complete results

[Evidence](evidence.json) retains all planned rows and source bindings. In the
table, a dash is unexecuted, never an observed failure.

| Control | 72 goals / width 4 / 216 rows | 96 goals / width 4 / 288 rows | 96 goals / width 4 / 384 rows |
|---|---:|---:|---:|
| Full reference | 12/12 | 12/12 | 2/12; 10 initial searches exceeded the limit |
| Greedy | 0/12 | 0/12 | 0/12 |
| Rarest goal | 0/12 | 0/12 | 0/12 |
| Greedy with work slack | 12/12 | 12/12 | 12/12 |
| Rarest goal with work slack | 12/12 | 12/12 | 12/12 |
| No recovery | 0/12 | 0/12 | 0/2 executed; 10 — |
| No recovery, stable world | 12/12 | 12/12 | 2/2 executed; 10 — |
| Offline gate | Pass | Pass | Not passed |

The reference performs 62 searches: 52 found plans, 10 exhausted the declared
limit. The last candidate reaches recovery only for seeds 0 and 5; there are no
invented recovery searches for its other seeds. It is mathematically
constructively solvable, but this bounded reference has not completed its sample.
Do not filter those ten seeds out or reinterpret the missing controls as successes.

| Candidate | Maximum initial states | Maximum recovery states | Maximum completed search seconds |
|---|---:|---:|---:|
| 72 / 4 / 216 | 9,150 | 1,433 | 0.087 |
| 96 / 4 / 288 | 67,056 | 7,052 | 0.743 |
| 96 / 4 / 384 | More than 1,000,000 in 10/12 cases | 695,398 among only 2 reached cases | Completed-only time does not summarize the censored distribution |

The first two candidates require 18/24 initial builds and 17/23 recovery builds.
Their subsecond specialized searches on this machine prevent any claim of broad
solver-assisted difficulty. Neither an offline pass nor high direct-model input
size proves frontier headroom.

## Promotion boundary

An offline pass requires all sampled reference completions, the expected
heuristic/non-recovery failures, and their corresponding successful rescue
ablations. Missing prerequisites or search-limit failures block that gate.
Passing supports further development of the candidate, not a frontier-difficulty
label. Strong-model calibration, solver-assisted configurations and structural
holdouts remain separate requirements in the [difficulty contract](../../docs/DIFFICULTY.md).

Next, give the two passing candidates an explicit experimental generator version
and integrate their frozen definitions with the existing collection path before
model calibration. Keep all four released anchors. Declare direct-model and
solver-assisted tracks separately and reserve unseen structures before tuning.
Keep the third candidate's whole distribution for a separately declared
reference/budget experiment; it has not passed the present gate and is not
discarded merely for being harder.
