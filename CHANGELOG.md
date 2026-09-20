# Changelog

## 2.5.0 — 2026-09-20

- Make high, adjustable and empirically discriminating difficulty a core acceptance
  requirement, with strong-model calibration, ceiling/floor checks and versioned anchors.
- Add `dependency-cover/1`: discover overlapping operations, plan within work
  limits, preserve valid progress and rebuild selectively after an announced change.
- Add four structural scales, a public-information exact reference, maximum-coverage
  and rarest-goal heuristics, plus budget and recovery rescue ablations.
- Reuse the existing collector, checkpoint/resume, replay, reporting and HTTP
  adapters. No plugin registry or second durable collector. Diagnostic-only metrics
  stay null; generator versions cannot silently mix within one suite.
- Add resource-preserving atomic batch actions so task size need not multiply
  provider calls. Record the fixed 192-episode offline matrix and a separately
  frozen four-episode public strong-model calibration plan.

**Comparability:** diagnostic semantics are unchanged; 2.0–2.4 traces remain
replayable. The new generator/action contract exists only from 2.5, uses `open`,
and is not pooled with old scores. Named scales do not yet establish measured
frontier difficulty. The P3.1 prototype remains unchanged and separately versioned.

## P3.1 development milestone — 2026-09-20

- Add the separately versioned `dependency-recovery/1` prototype: a probe reveals
  an unavailable preparation operation; an announced dependency replacement
  invalidates a prior PASS and completed work, requiring discovery and rebuilding.
- Add visible/hidden and stable/changing ablations, five public-information
  policies, an independent public-history acceptance check, strict replay and
  complete-matrix validation. Publish all 60 public development trajectories.
- Reject unrevealed handle guesses, stale operations, old verification, evidence
  edits and incomplete control matrices. Test relabeling, future-information
  noninterference, exact budget/horizon boundaries and exclusive report creation.
- Keep random generation, live model calls, diagnostic metric pooling and a
  second durable collector out of this prototype. Update P3's next decision gate
  to meaningful structural generation and reuse of the existing evidence path.

**Comparability:** the scored framework remains 2.4 with unchanged diagnostic
semantics. Prototype fixtures are engineering controls, not independent samples,
model scores or real-work evidence. New package source changes collection
fingerprints; resume existing runs in their original checkout.

## 2.4.0 — 2026-09-18

- Correct the 2.3 parser's rejection of documented reasoning content parts; bind parts to declared item identities and ignore reasoning as action content.
- Use the explicitly requested SSE format when an endpoint omits its media header. Preserve completion checks without guessing from body text.
- Assemble completed output items when the native terminal envelope omits/repeats no output; require item closure and whole-response completion, and reject conflicting completed actions.
- Permit an explicit environment-only account selector. The local launcher supplies request-scoped existing authentication without changing shared-session settings or starting an agent runtime.
- Add positive/negative protocol fixtures and an independent [four-episode validation plan](studies/direct-channel-validation-v2/README.md). Preserve all earlier failure evidence.
- Complete and replay all four attempts: both models delivered their cascade task; the two diagnosis attempts retained a stream failure and a request timeout. Report 19 requests, 17 complete usage records and the failed all-four gate.
- After frozen collection, retain usage when a completed stream contains invalid action JSON. The final release passes 105 tests; live evidence remains bound to its earlier 104-test source commit.

**Comparability:** no generator, public prompt, transition or grader changes. Authentication, stream parsing and declared integration limits differ from the prior pilot; do not pool the runs.

## 2.3.0 — 2026-09-18

- Remove the experimental Codex app-server bridge from the preferred live collection path; add direct Responses support over the same HTTP transport as Chat Completions.
- Explicitly request no tools and no response chaining. Reject tool-bearing, truncated, ambiguous or unfinished output instead of accepting the first JSON-looking text.
- Enforce one active-socket deadline, including slow headers and body reads; reject redirects, oversized responses and truncated HTTP bodies. No implicit proxy discovery or benchmark retries.
- Preserve request fingerprints, declared tool policy and sanitized failure categories without raw provider bodies, credentials or reasoning.
- Support explicit environment-only gateway X- headers, including exact-route selection; avoid claiming that local configuration attests upstream behavior.
- Publish a new [four-episode integration plan](studies/direct-channel-validation-v1/README.md) before collection. Preserve the earlier eight-episode reminder pilot unchanged.
- Retain and replay all four first-request integration failures (two HTTP 401, two stream-part rejections). Publish a separate successful constant-output diagnostic without substituting it for multi-turn acceptance. Require endpoint authorization and protocol compatibility before further collection.

**Comparability:** task generation, public environment prompts and acceptance are unchanged. The HTTP request and response contract is stricter; existing 2.0–2.2 traces replay, but new collections require 2.3 source/configuration. The new protocol cannot be pooled with earlier native-runtime runs.

## 2.2.0 — 2026-09-18

- Add a frozen single-reminder contrast against an equal-word neutral control, without changing old conditions or generator semantics.
- Add strict study plans and `prepare-study`: fresh private seeds, complete declared structural distributions, plan/prompt fingerprints and fixed stopping rules.
- Reuse the existing collector with adjacent counterbalanced pairs; suppress unplanned cross-model primary comparisons.
- Add seed-level Hoeffding intervals with simultaneous coverage across declared agents, an explicit confirmatory precision gate, and separate execution-censoring identification bounds.
- Add a public-information budget-omission sensitivity control plus ceiling/floor controls and tests across 96 structural instances.
- Remove the arbitrary 60-second maximum for explicitly configured request timeouts; remaining episode time still caps every call.
- Publish the [live feasibility pilot plan](studies/verification-reserve-pilot-v1/README.md) before collection. Small pilots remain exploratory, including at perfect success.
- Complete and replay all eight live pilot episodes, retaining two bridge failures. Publish the omitted native image-generation switch and full-width primary intervals; stop scaling because feasibility and target-failure evidence are insufficient.

**Comparability:** the two new prompt conditions exist only from 2.2. Old traces remain replayable, but source/version changes require fresh collection directories. This release supports inference about the declared reminder contrast, not training causes or real-work predictive validity.

## 2.1.0 — 2026-09-18

- Replace the unordered research wish list with dependency gates, explicit deletions/deferrals and executable acceptance criteria; add a Chinese roadmap.
- Add `prepare`, `status` and strict `resume` over one frozen serial matrix, without retrying any started episode.
- Persist request-boundary checkpoints, immutable starts and trace receipts; preserve completed evidence and conservatively account for interrupted attempts.
- Use an OS process lock and verify source/Python/platform identity before continuation.
- Consolidate suite validation, matrix/evidence validation and summary generation; reject mixed-version pooling and validate recorded cost bounds.
- Preserve 2.0 environment replay and historical study bytes. Add real process-crash, competing-process and commit-boundary tests.
- Publish [offline and live local-model integration evidence](studies/framework-v21-validation/README.md), retaining a bridge timeout and unknown failed-request usage without interpreting it as a model ranking.

**Comparability:** generator, public observations, action semantics, prompts and task acceptance are unchanged. Collection interruption accounting is new and explicitly versioned. 2.0 runs remain readable but cannot be resumed because they lack request-boundary evidence. Exact collection compatibility and limits are in [COLLECTION.md](docs/COLLECTION.md).

## 2.0.0 — 2026-09-18

The project now provides a generative evaluation framework for future agents. The original two-model comparison is indexed and frozen as a historical study.

- Add deterministic, versioned diagnostic graph generation with variable costs, partitions, noise and sequential revelation.
- Add an observation-limited minimax reference, random policy, overdiagnosis control and proxy-gaming control.
- Add a state-revision acceptance predicate: passing verification must follow the final mutation, and the agent must explicitly finish.
- Add a provider-neutral JSON-action adapter with environment-only credentials and no model filesystem tools.
- Add arbitrary agent names, manifests, source hashes, complete matrix validation, trace replay and failure-inclusive statistics.
- Cluster bootstrap uncertainty by generation seed; distinguish prompt rescue from identified intrinsic autonomy.
- Add protocol/design/validity/related-work/roadmap documentation and bilingual entry points.
- Preserve all historical source/data/report bytes and document v1 side channels and scorer limitations.

**Comparability:** v2 is a new environment, grader and harness. Its scores cannot be pooled with the v1 GPT/GLM results. Scripted control validation and localhost adapter tests establish implementation behavior, not frontier-model performance or real-work predictive validity.

## Historical release — 2026-09-18

Published the original incident simulator, 72 trajectories, analysis, reports and Codex runner under Apache-2.0. The historical snapshot is commit `cc44d68690db7dded3caf43183ac2908373ca635`.
