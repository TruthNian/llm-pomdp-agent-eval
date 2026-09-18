# Development roadmap and decision gates

[中文路线图](ROADMAP.zh-CN.md) · [Design](DESIGN.md) · [Collection contract](COLLECTION.md)

The enduring question is whether an agent can turn incomplete information into an accepted outcome under resource constraints. A model name, training story, larger catalogue or higher score is not itself progress toward answering that question.

## Working order

Apply the requested five-step method in order: **question requirements → delete unnecessary parts → simplify and optimize → shorten feedback cycles → automate**. The first three steps are release gates. Faster collection is useful only after the collection measures the intended behavior.

Before adding a feature, record the decision it enables, the failure of the smallest existing solution, an observable acceptance test, and a removal condition. Preserve published evidence even when its interpretation is corrected. Deleting an unsupported claim is different from deleting an inconvenient result.

## Requirements questioned in this iteration

| Assumption | Decision | Evidence or return condition |
|---|---|---|
| More scenario names imply broader competence | Do not expand semantic skins for coverage claims | A new family must change the information/action structure and distinguish relevant policies |
| A bundled procedural prompt explains why a model improves | Retain it as a sensitivity check; postpone mechanism claims | P2 requires isolated interventions and matched contrasts |
| Repeating an interrupted run is harmless | Remove this as the recovery workflow | P1 preserves completed episodes and interrupted failures without redialing them |
| Repeated validation implementations are safer | Delete duplicate suite/matrix/summary paths | One definition validator, one evidence validator, one summary builder |
| A software update can be silently mixed into collection | Reject changed runtime/source on resume and mixed versions in summaries | Historical replay is separate from continuing an experiment |
| Concurrent workers, automatic retries, plugin systems and dashboards are prerequisites | Defer them | Add only after a measured bottleneck or a second independent family requires them |
| A single autonomy score is necessary | Do not introduce one | An application must first declare its utility and show the aggregation is useful |

## Dependency order

```text
P0: valid measurement kernel [delivered in 2.0]
  → P1: reliable evidence collection [delivered in 2.1; offline acceptance passed]
  → P2: isolate an intervention mechanism [2.2 study workflow; empirical gate remains open]
  → P3: structurally different tasks requiring discovery and recovery
  → P4: prospective validation against real delegated work
  → P5: scale only the useful, validated parts
```

This is an order of evidence, not a calendar promise. A failed gate returns to its assumption or implementation; it does not justify collecting more of the same data. P2 and P3 can be explored separately after P1, but neither supports deployment predictions before P4.

## P0 — Preserve the minimum valid kernel

**Status:** delivered in 2.0. Public projection, truth-independent solvability budgets, revision-aware verification, explicit handover, positive/negative controls, replay, seed-clustered statistics and frozen historical studies exist.

**Keep:** these properties as regression constraints. **Do not claim:** unknown-hypothesis discovery, independent domains, real-work prediction or an intrinsic autonomy trait from the current diagnostic kernel.

Acceptance remains the environment/reference tests and [published control validation](../studies/framework-v2-validation/README.md). A family that cannot fail designed bad policies must not enter scored evaluation.

## P1 — Make collection inspectable and recoverable

**Status:** implemented in 2.1. Offline tests, cross-platform CI and a four-episode local model pilot are documented in the [validation record](../studies/framework-v21-validation/README.md), including one bridge timeout. Scope is serial, one-attempt collection with local evidence files; no scheduler service or database.

| Work item | Delivered behavior | Acceptance evidence |
|---|---|---|
| P1.1 Freeze before spending | `prepare` validates the full matrix and records its ordered schedule fingerprint without model requests | CLI preparation test; invalid definitions create no run |
| P1.2 Recover without selection bias | `resume` retains completed successes/failures; seals interrupted attempts; executes only unstarted entries | Request-boundary, process-crash and no-redial tests |
| P1.3 Bind evidence to the run | Immutable starts and receipts bind manifest/trace hashes; checkpoints retain public events | Modified/deleted trace, manifest drift and commit-boundary tests |
| P1.4 Prevent conflicting writers and runtime drift | OS lock; exact source/Python/platform check before resume | Competing-process and source-drift tests |
| P1.5 One verification path | Run, resume, validate and summarize share matrix/replay validation | Existing runner tests plus new collection tests |
| P1.6 Keep historical interpretation stable | 2.0 replay remains readable; collection failures are explicit; mixed-version pooling is rejected | Version, cost-bound, denominator and usage tests |

**Exit gate:** full tests, frozen-study checks, offline demo/replay, Windows/Linux CI. A live provider pilot checks transport and configuration separately; it is not a model ranking. Missing usage and uncertain in-flight requests remain unknown. Local hashes are consistency checks, not adversarial attestation.

**Deliberately deferred:** implicit retries, parallel workers, cross-runtime resume, public raw-run export and provider-checkpoint attestation. Revisit a deferral only with a failure or measured need. See [exact interruption semantics](COLLECTION.md).

## P2 — Test one mechanism before expanding the factorial design

**Implementation:** 2.2 provides a strict plan format, an equal-word neutral control versus one budget reminder, fresh-seed preparation, counterbalanced adjacent pairs, a conservative seed-level primary interval and execution-censoring bounds. It reuses the existing collector. See [the study contract](STUDIES.md) and the [predeclared live pilot](../studies/verification-reserve-pilot-v1/README.md). An implemented protocol is not yet an identified effect.

**Pilot decision:** all eight planned trajectories replayed. GPT accepted both arms on both seeds; both GLM neutral episodes were interrupted by the execution channel (an unexpected hosted-tool item and an event timeout). No observed budget failure supports scaling this reminder study. The native bridge also omitted the independent image-generation feature switch. Preserve the result, verify effective capability isolation and transport before any new pilot, and then reconsider task headroom. Both primary intervals span [-1,1]; the apparent GLM delivery gain cannot be interpreted as a budgeting rescue.

**Question:** does an isolated piece of policy assistance change accepted completion and its associated observable failure, on identical cases and budgets?

1. Write a versioned study plan before inspecting evaluation outcomes: hypothesis, primary contrast, minimum useful effect, task distribution, models/settings, budgets, stopping rule and handling of infrastructure failures.
2. Start with one intervention, such as reserving final verification resources, against the unchanged public contract. Freeze exact prompt text. Do not simultaneously add a planner, candidate-state table, memory aid and verification checklist.
3. Supply executable positive/negative controls showing that the measured failure can occur and that the proposed assistance addresses it. If the control cannot distinguish the policies, change the task before making model calls.
4. Estimate required independent seed count from a separate development pilot and a declared precision/power calculation. Repeats and semantic skins do not increase the number of independent tasks.
5. Collect all configurations on the same frozen cases/noise schedule. Report accepted outcomes, resource costs, failure types and matched seed-clustered uncertainty. Separate infrastructure failures from task failures while retaining the full denominator.
6. Only if the first mechanism is distinguishable, add a second factor and a preregistered interaction contrast. A full four-factor design is not the default.

**Deliverables:** a small validated study-plan schema, versioned intervention text, a plan-bound collector, explicit primary contrasts, and a frozen study report containing every planned attempt.

**Exit gate:** no post-hoc exclusions, identifiable contrast, independently reproduced controls, useful uncertainty across multiple model configurations, and an account of ceiling/floor effects. Claim only sensitivity to the specified intervention. Stop expanding this family if it cannot discriminate beyond the reference policy's already-known solution.

## P3 — Add one genuinely new structure, including recovery

**Question:** can the agent discover what actions or hypotheses are possible, revise its understanding and recover when intermediate progress changes the problem?

Start with one generated dependency-discovery environment. A public probe reveals a local dependency; an intervention can unlock a previously unavailable operation; a recoverable external change can invalidate an earlier plan. Specify which information is initially unavailable and which actions acquire it. Do not begin with a plugin registry or unrestricted shell.

**Deliverables:** public observation/transition contract, isolated evaluator, independent acceptance predicate, public-information constructive witness, and versioned generator. Add comparison policies that stop too early, follow a static checklist, never revise a plan, and overspend on investigation.

**Exit gate:** unknown dependencies materially affect decisions; the successful witness needs discovery and at least one controlled recovery path; harmless exploration is distinguishable from avoidable mistakes using information available at the time; fresh structure defeats at least one old fixed policy without destroying solvability. Document which construct is new and which is still absent.

**Removal rule:** if the family is equivalent to choosing another label from an already complete catalogue, simplify it back into a diagnostic profile and drop the broader claim.

## P4 — Test whether the benchmark predicts real outcomes

Freeze an externally scored sample of real delegated tasks and a rubric for acceptance and human intervention time. Score benchmark configurations before revealing those outcomes. Compare prediction with static domain-skill and simple cost baselines; hold out task sources, not merely repeated runs.

**Deliverables:** consent/privacy-reviewed data protocol, preregistered analysis, task-level uncertainty, baseline comparisons and a report including null results.

**Exit gate:** useful prospective prediction beyond the baselines, or an explicit negative result narrowing the benchmark's purpose. Synthetic differences alone cannot close this gate. Do not substitute a simulator's hypothetical intervention count for measured human time.

## P5 — Accelerate and automate what survived the earlier gates

Profile actual collection, replay, analysis and maintenance costs. Remove avoidable recomputation before introducing parallel scheduling. Add concurrency only with endpoint rate limits, fair scheduling, interruption tests and immutable attempt accounting. Add family plugins only after two independent implementations expose a stable shared interface. Add recurring evaluation only when version drift and alert criteria are defined.

**Exit gate:** documented before/after cost or latency, unchanged measurement semantics, fault tests, and a named maintenance owner. Remove automation that produces noise rather than a decision.

## Evidence and dataset lifecycle

Public development seeds support debugging; private evaluation seeds support prospective collection; held-out structures test a different generalization claim. Retire and publish reviewed manifests/traces with versioned sources and exclusions. Never silently change a released study or erase failed collection attempts. New seeds alone do not establish contamination resistance.

The next work is **verify the live action channel before collecting more model evidence**: remove undeclared hosted capabilities, check effective configuration, and distinguish runtime events from valid JSON actions. A revised bridge needs its own frozen source and study plan. Then test whether the task distribution has observable target failures; do not expand the completed pilot or infer mechanisms from its censored contrast. P3's observation/transition design can proceed independently, but it does not close this empirical gate.
