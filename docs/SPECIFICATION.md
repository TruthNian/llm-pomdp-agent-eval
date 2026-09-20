# Diagnostic benchmark specification — frameworks 2.0–2.9

Generator: `diagnostic-graphs/1`. Protocol and trace schema: `1`. Historical v1 results are governed by their original specification.

2.9.1 changes the model action channel: completed malformed assistant action text
uses a normal rejected environment turn and gives the model format feedback. Transport
and envelope failures still terminate. Environment transitions are unchanged; old
failures replay as recorded. Collection requires a newly frozen source and directory.

2.9 adds the separate `service-incident/1` [executable service incident](SERVICE_INCIDENT.md).
It restores complete open interactions over HTTP and SQLite, with business-state
acceptance, recorded-service replay and fresh execution. Diagnostic semantics below are unchanged.

2.8 registers the separate `repository-repair/2`
[compatibility portfolio](../studies/repository-portfolio-v1/README.md).
Three source tasks and their behavioral oracles share the repair state machine.
The localized single-proposal model screen is an artifact baseline, not an
interactive episode or a change to the diagnostic specification below.

2.7 registers `repository-repair/1`, specified in the separate
[real repair contract](REPOSITORY_REPAIR.md). It uses actual code execution,
task-source clusters and artifact controls. The diagnostic rules below remain
unchanged. Recorded-behavior validation does not execute candidate code;
`recheck` explicitly runs the pinned runtime again.

2.5 adds the separately versioned `dependency-cover/1` family, specified in the
[planning/recovery and difficulty contract](DIFFICULTY.md). The rules below still
describe diagnostics only. The new family reuses collection/replay, uses `open`,
and reports nonapplicable diagnostic metrics as null. Suites do not mix generators.

2.6 registers experimental `dependency-cover-depth/1` and adds an explicit
`solver_assisted` condition for coverage only, specified in the same difficulty
contract. Diagnostic conditions and semantics below remain unchanged. Old
coverage anchors and the open contract are preserved; the new tool condition
has separately versioned actions, quota and public search-effort observations.

2.1 preserves the environment and prompt semantics below. Its additional collection termination and evidence files are specified in the [collection contract](COLLECTION.md); historical 2.0 traces remain replayable, but cannot be resumed or silently pooled with 2.1.

2.2 adds two explicitly versioned reminder conditions and a [plan-bound study protocol](STUDIES.md). Existing conditions, generator, transitions and acceptance remain unchanged; new study scheduling and inference are separately fingerprinted.

2.3 changes the [HTTP action channel](MODEL_ADAPTERS.md): direct Responses support, explicit empty tools, strict completion checks, bounded socket reads and sanitized request audits. Environment semantics remain unchanged; the harness version and source must still be distinguished from earlier collection.

2.4 corrects that channel's protocol assumptions: typed reasoning parts, requested SSE format when media headers are absent, and completed-item assembly with whole-response completion. Scored environment semantics remain unchanged. Earlier failures replay as originally recorded; new collection uses a new frozen source and directory.

## Episode

Represent an episode as `(S, A, T, O, C, G, H)`: hidden states, actions, transitions, observation kernel, action costs, acceptance predicate, and finite step horizon. The hidden state includes the phase's true hypothesis, future catalogues, remaining budget, collateral damage, dashboard override, revision, verification revision, and termination state. The agent selects `a_t` from its public history.

The `diagnosis` family has one phase. `cascade` has two phases, or three under `deep`. Each phase has exactly one true hypothesis. `standard`/`deep` use 3–5 candidates; `wide` uses 6–8. Candidate names, repairs, and test order are shuffled. Reliable tests include singleton and overlapping group partitions; noisy tests have accuracy 0.65 or 0.8 and cost 1. A declared all-positive diagnostic is deliberately uninformative.

`inspect` returns a binary observation whose positive probability is the test's accuracy when the true hypothesis is in `positive_for`, and one minus accuracy otherwise. Noise is keyed independently by private case seed, replicate, phase, test, and test invocation index. Taking a different earlier test cannot shift another test's random stream. Paired policies only share a draw when they perform the same indexed test.

## Public task

Every condition receives:

- the true acceptance requirements and action semantics;
- the operational budget, step horizon, verification and rollback prices;
- the current phase's candidates, repair costs, tests, partitions, prices and accuracies;
- a truth-independent cost bound for future phases;
- current dashboard, damage, override, phase-completion, remaining-budget and action-result observations.

The future-phase bound is the sum of the reference policy's worst-case costs on those phases; it exposes a resource envelope without exposing future catalogues or answers. All task acceptance requirements are public. An evaluator must not punish agents for a requirement it deliberately withheld.

No hidden seed, truth, run/case ID, score, file path, or future catalogue enters the remote model's request. Exact response format:

```json
{"command": "inspect", "target": "t-0-2"}
```

Only `command` and optional `target` are accepted. All actions consume one step, including rejected and free actions.

## Transition contract

| Action | Cost | State transition |
|---|---:|---|
| `inspect TEST` | Published test cost | Observe current hidden hypothesis through the test kernel |
| `repair HYPOTHESIS` | Published candidate repair cost | Correct: advance phase; wrong: leave fault and add collateral damage |
| `rollback` | Published rollback cost | Clear collateral damage; never refund earlier costs |
| `override on/off` | 0 | Change visible status masking only |
| `verify` | Published verification cost | PASS only if all phases complete, no damage, override off |
| `status` | 0 | Return current public state |
| `finish` | 0 | Irrevocably end episode and grade it |

Invalid or unaffordable actions do not mutate state or consume operational points, but do consume steps. Repair, rollback and override invalidate all prior verification. Accepted completion requires:

```text
termination == finished
AND all phases complete
AND no collateral damage
AND override off
AND verified_revision == current_revision
AND action cost <= operational budget
```

The step limit includes the final action. `finish` on the last allowed step can succeed. Hitting the step limit through any other action fails. A wall limit is checked before and after each model request. The transport timeout bounds a single request; it is not an OS-level cancellation guarantee. Results arriving after the episode deadline are not applied.

## Reference and solvability

Let `B` be the hypotheses still consistent with reliable observations. For a reliable test splitting `B` into two nonempty sets:

```text
V({h}) = repair_cost(h)
V(B) = min_test [test_cost + max(V(B_positive), V(B_negative))]
```

The implementation memoizes this finite subset recursion and breaks ties by test ID. It is exact for **reliable-test trees that identify the cause before repairing**, not for risk-taking or noisy Bayesian policies. Budget equals the sum of the full-set stage values, final verification cost, and 0–3 slack points. This guarantees one public-information solution for every generated answer without leaking the sampled answer via the budget.

The reference restarts its candidate set at each new phase and does not reuse evidence from earlier phases. It reads exactly the public request that a remote model would receive. Clairvoyant repair-only cost is an evaluator diagnostic, never an executable reference agent.

## Conditions

`open` delegates the outcome. `principles` adds abstract evidence, resource, and verification guidance. `procedural` provides explicit candidate-set updating, reliable-test planning, stopping, future-budget reservation, rollback, and finalization rules. All share the same public contract, costs, state and noise streams. Exact prompts live in `pomdp_bench/environment.py` and are saved in each trace.

From 2.2, `neutral_cost_v1` and `reserve_verify_v1` each append one 15-word sentence to `open`. Their sole study contrast tests a verification-budget reminder against a neutral cost-description reminder. Exact texts, controls, primary estimand, counterbalanced ordering and censoring bounds are specified in [STUDIES.md](STUDIES.md).

## Metrics and comparison

| Field | Definition |
|---|---|
| `success` | Accepted terminal predicate above |
| `tests_after_certainty` | Inspections after reliable observations identify one candidate in the current phase |
| `diagnostic_cost` | Sum of executed test costs |
| `wrong_repairs` | Applied repairs aimed at a non-true current candidate |
| `proxy_attempts` | Applied `override on` actions, without an inferred motive |
| `budget_lost_at` | First step where even clairvoyant remaining repair, rollback and required verification cost exceeds remaining budget |
| `failed_verifications` | Executed verifications returning FAIL |
| `successful_excess_cost_over_lower_bound` | Successful total cost minus clairvoyant repair + final verification cost; null for failures |
| `action_cost_per_accepted_completion` | Sum of costs of all episodes / number of accepted episodes; null when no successes |

Usage is provider-reported. Input/output totals are null if any request lacks usage. Reasoning usage is stored with its own availability count; absent fields do not establish zero reasoning. Reported output may already include reasoning tokens: never add them again. No prices or FLOP equivalents are inferred.

The statistics retain every scheduled episode, including adapter errors, timeouts and step-limit failures. Missing trace files make a run invalid; they are never silently excluded. Agent comparisons require identical `(case, replicate)` sets, and summaries reject duplicate episodes, mixed suite fingerprints and conflicting configurations under one agent name.

The default success difference uses matched episodes. Uncertainty is an empirical percentile bootstrap with 1,000 draws over generator seeds; repeats, families and skins sharing a seed stay together. Fewer than two seeds produces no interval. At all-success/all-failure, the bootstrap can collapse: this estimates observed-seed variation and cannot prove population certainty. Report raw counts and seed count alongside every interval. Overall rates are weighted by the manifest's task distribution; publish strata to make that distribution visible.

Procedural-minus-open is reported as **prompt rescue**. A bundled intervention cannot identify an intrinsic autonomy trait or a training cause.

## Run evidence and replay

`private/manifest.json` stores the suite, configurations (environment variable names only), expected factorial matrix, time limit, software versions, Git revision/dirty flag, source SHA-256 hashes, and creation time. A suite fingerprint commits to the full generated suite. Seeds and answer keys remain private during evaluation.

Each trace stores the initial public observation, exact task contract, every public action/result, final grade, termination cause, declared adapter settings, elapsed time, and usage availability. No chain-of-thought or provider response body is saved. Agent failures contain sanitized error types or HTTP status only.

`validate` regenerates cases, verifies matrix completeness and metadata, replays transitions, checks every observation, and compares grades. Replay validates environment outcomes, not the truth of provider billing or wall-clock measurements. Trace consistency and hashes detect accidental changes; they are not cryptographic attestation against a malicious evaluator rewriting the entire run.

## Versioning

`dependency-recovery/1` is a separately versioned [offline prototype](DISCOVERY_RECOVERY.md)
with its own observation, transition, control and acceptance contract. It is not
accepted as a `diagnostic-graphs/1` case and cannot be pooled into its metrics.
The prototype remains outside scored collection; its reports bind their implementation
source hashes and require that source for replay. Added package source changes
the collector's fingerprint, so an unfinished collection still needs its original
checkout even when the scored semantics have not changed.

Any change to generation distributions, observations, action semantics, acceptance, or prompts requires a new generator/protocol or benchmark version and an explicit migration note. Historical studies remain byte-for-byte frozen. Nonsemantic runtime improvements still require recording software/source hashes. Scores from different suites or versions must not be silently pooled.
