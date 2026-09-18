# Changelog

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
