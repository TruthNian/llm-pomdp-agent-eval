# Difficulty is a measurement requirement

An easy benchmark that every relevant model solves cannot support the intended
comparison. An impossible benchmark that every model fails has the same problem.
The goal is **high, adjustable, demonstrably discriminating difficulty**, with a
solvable core and room above the current measured frontier. Difficulty is a
release gate, not a promise inferred from task length or a profile name.

## Question, delete, simplify

- The P3.1 nine-step prototype admits a short fixed reactive policy. Keep it as a
  contract/regression test; do not promote its success rate into a hard benchmark.
- Increasing labels, prose, calls or chain length alone does not establish deeper
  decisions. Require a competent heuristic to fail where a public-information
  reference succeeds, then check current strong model configurations.
- Delete dependence on hundreds of serial model calls. Batching reads/builds costs
  exactly the same operational resources; it changes request overhead explicitly.
- Keep one new planning problem: select compatible overlapping operations under
  a finite work allowance, then reuse still-valid work after selective invalidation.
  Avoid adding unrelated domain knowledge, obscure instructions or hidden rubrics.

## Versioned structural ladder

`dependency-cover/1` is available from framework 2.5. It is separate from both
`diagnostic-graphs/1` and the frozen `dependency-recovery/1` prototype.

Framework 2.5.1 adds `dependency-cover-actions/2`: explicit JSON examples and
fixed schema feedback after invalid actions. Generation, work limits and scoring
remain unchanged. Historical 2.5.0 replay selects its original action contract;
new and old framework versions are not pooled. Removing ambiguity in the action
interface prevents schema friction from masquerading as planning difficulty.

| Scale | Goals | Goals per operation | Alternative operations | Initial work | Recovery work |
|---|---:|---:|---:|---:|---:|
| sanity | 6 | 2 | 9 | 3 | 2 |
| challenge | 18 | 3 | 36 | 6 | 5 |
| hard | 32 | 4 | 64 | 8 | 7 |
| extreme | 48 | 6 | 96 | 8 | 7 |

Labels describe structural scale. Neither monotonic model difficulty nor a
frontier-level threshold has been established by these names. Larger set systems
can occasionally be easier; report each scale, generator seed and configuration.
The meaningful pressure is global compatibility: under the default work limit,
overlap consumes capacity needed by another goal. Selecting the most immediate
coverage, even starting with the least-supported goal, can leave no completion.

Generation embeds a feasible partition, adds distinct overlapping alternatives,
then shuffles operation assignments. No solution labels are retained or given to
the agent. The generator is a declared distribution, not all possible hard cover
problems. A specialized solver can exploit its public structure. A second task
distribution or external work must test transfer separately.

## Public task and transitions

The initial observation lists goals and operation IDs, but no operation coverage.
`probe` reveals current coverage, enabling that operation's build. Each operation
covers exactly the advertised width. Acceptance requires covering all goals,
verification at the latest revision and explicit finish.

| Action | JSON target | Resources / state |
|---|---|---|
| `probe` | One operation ID or `"all"` | One inspection and action point per row, including redundant probes; reveal current coverage |
| `build` | Nonempty array of distinct freshly probed IDs | One work unit and action point per ID; union its coverage into completed goals; increment revision |
| `verify` | None | One action point; PASS iff all goals are covered; record checked revision |
| `status` | None | Free public observation |
| `finish` | None | Irreversible handover |

A batch is validated atomically. Invalid, unaffordable, duplicate or unrevealed
members reject the entire batch without spending resources or applying a prefix.
Every action consumes one step; batches consume one step. Invalid and blocked
actions also consume steps. Rebuilding already covered goals still spends work
and invalidates verification. No refunds or implicit retries exist.

With recovery enabled, the first PASS triggers one announced change. A fixed-size
subset of goals loses coverage; all other completed goals remain valid. The
operation descriptions expire and their new coverage must be probed. The new work
allowance starts, earlier costs remain spent, and the prior PASS is obsolete. The
replacement matrix contains a feasible cover of the affected subset within its
allowance. The subset identity and future matrix remain hidden until their
respective change/probe observations. This is a disclosed, deterministic stress
transition, not learned or arbitrary real-world dynamics.

## Solvability and reference

Budgets depend only on scale, recovery and explicitly declared slack, never on
sampled operation assignments or the changed-goal identity. Inspections allow one
complete scan per epoch. Total action points cover those scans, work allowances
and one verification per epoch. The step horizon additionally allows 12 actions
beyond the per-row/per-build resource envelope; free actions cannot extend it.

The generator constructs at least one feasible initial partition and one
partition of the affected goals. Therefore a policy that reveals each epoch's
matrix and finds its cover is feasible for every generated instance, independently
of which partition was embedded. The reference searches **only revealed rows**,
branches on a least-supported uncovered goal, prunes capacity-infeasible branches
and memoizes uncovered-goal/remaining-work states. It minimizes additional builds
within the work allowance, not total probing cost or unrestricted POMDP cost.

The reference has an explicit one-million-state search limit per decision. An
exhausted search raises a recorded internal failure; it never certifies an
instance impossible. Mathematical existence does not guarantee a cheap reference
search on every future sample. A reference-limit failure blocks that calibration
gate and stays in the matrix. Supported scales are bounded; new scales require
versioning and runtime/solvability checks rather than silently increasing defaults.

The scorer's lower bound omits inspections, divides missing goals by maximum
coverage and includes required verification/recovery. It is a clairvoyant lower
bound, not an executable policy. The reference guarantee and this diagnostic are
separate claims.

## Shared evidence path and meaningful metrics

```bash
python -m pomdp_bench generate-cover --fresh --count 12 --scales sanity challenge hard extreme --out artifacts/private/cover.json
python -m pomdp_bench prepare --suite artifacts/private/cover.json --agents examples/coverage-agents.json --out artifacts/cover
python -m pomdp_bench resume artifacts/cover
python -m pomdp_bench validate artifacts/cover
```

Use `--seed 0` for public development cases. `--stable` removes the change and
`--slack N` adds work allowance to each epoch. These are different declared task
distributions; they never replace a failed default trial. Extra work must rescue
the resource-limited heuristic, and removing the change must rescue the
non-revising policy. A control failure alone is insufficient construct evidence.

The family reuses the existing prepare/start/checkpoint/receipt/resume/replay
implementation and the same HTTP adapters. One suite contains one generator;
only `open` applies. Diagnostic-only measurements are `null`, not fabricated
zeroes. Success, resource cost, work, inspections, time, usage availability and
infrastructure failures are reported separately, by scale. Do not pool default
scales into an arbitrary autonomy score. The prototype and all earlier studies
remain unchanged; old runs replay, but source/version drift still forbids resume.

## Calibration and long-term maintenance gate

1. Freeze generator, scales, prompts, budgets, model/reasoning settings and a
   complete development matrix before requests. Keep every failure and unknown
   usage. Transport failures cannot demonstrate cognitive difficulty.
2. Check a public-information reference, maximum-new-coverage heuristic,
   rarest-goal-first heuristic and a policy that never recovers. Test the budget
   and recovery rescue ablations. A short reactive policy is only a sanity control.
3. Probe current strong models across the ladder. A small public pilot can detect
   obvious ceiling/floor or channel problems; it does not establish population
   difficulty, contamination resistance or a ranking.
4. Before claiming discrimination, collect an independently frozen matrix with
   at least 12 distinct private seeds per scale and multiple model/compute
   configurations. Twelve is a minimum screening requirement, not a power
   guarantee: declare required precision separately and report seed uncertainty.
   Require observable completed successes and task failures in the useful region;
   refuse readiness if outcomes are dominated by infrastructure or are uniformly
   perfect/failed. A parameter-size or training-cause claim needs further controls.
5. Track success and cost curves by immutable version and scale. Keep easy anchors
   for comparability, concentrate new evidence near the measured boundary, and
   reserve harder structures before tuning. If the strongest evaluated settings
   saturate the top scale, add and calibrate a new version with overlapping anchors.
   Do not rewrite old scores, drop failures, or adapt difficulty separately for
   competing models while comparing raw success rates.

The [first calibration record](../studies/coverage-calibration-v1/README.md) and
[corrected follow-up](../studies/coverage-calibration-v2/README.md)
distinguishes implemented structural difficulty from demonstrated model headroom.
Difficulty and discrimination are necessary; real-work predictive validity
remains a separate P4 gate.
