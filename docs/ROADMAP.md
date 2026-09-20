# Development roadmap and decision gates

[中文路线图](ROADMAP.zh-CN.md) · [Design](DESIGN.md) · [Collection contract](COLLECTION.md)

The enduring question is whether an agent can turn incomplete information into an accepted outcome under resource constraints. A model name, training story, larger catalogue or higher score is not itself progress toward answering that question.

**Persistent requirement:** high, adjustable and demonstrated discriminating
difficulty. Keep overlap with earlier scales as capabilities advance, but do not
let a saturated toy define the project's useful range. The [difficulty contract](DIFFICULTY.md)
makes solvability, strong baselines, model headroom and ceiling/floor checks explicit.

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
| One JSON action requires a complete native agent runtime | Remove the experimental runtime bridge from the preferred path | 2.3 shares one HTTP transport between Chat Completions and Responses; explicit empty tools, complete envelopes and one socket deadline |
| A listed model or a successful one-action probe establishes readiness | Delete that assumption | The 2.3 fixed pilot retained four first-request failures; a later constant-output probe passed without validating multi-turn input |
| Strict parsing means requiring one provider's exact envelope layout | Replace incidental layout requirements with completion and identity checks | 2.4 accepts typed reasoning and completed-item streams while rejecting tools, unfinished items and conflicting actions |
| Native authentication requires global session sharing | Remove the shared-state dependency from the validation launcher | Supply the explicitly authorized login on this client's requests; leave global login/router/consent files unchanged |
| Concurrent workers, automatic retries, plugin systems and dashboards are prerequisites | Defer them | Add only after a measured bottleneck or a second independent family requires them |
| A single autonomy score is necessary | Do not introduce one | An application must first declare its utility and show the aggregation is useful |
| Discovery needs a random generator and live model calls before its construct can be checked | Delete that dependency | `dependency-recovery/1` first tests a 2×2 ablation with fixed public fixtures and observation-only controls |
| A negative control failing proves the intended obstacle was measured | Require a rescue ablation | Static execution succeeds when the dependency is visible and stable; discovery without revision succeeds when replacement is removed |

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

### P1.7 — Remove unnecessary runtime authority

**Implemented in 2.3; offline acceptance passed, installed-route integration gate failed.** The [direct-channel validation](../studies/direct-channel-validation-v1/README.md) replaces the experimental app-server bridge with an ordinary HTTP call, shared between the two supported API formats. It deletes the native agent subprocess, capability denylist, bridge event queue and second request deadline from that path. Strict response parsing rejects tools mixed with valid text, truncation, ambiguous choices and incomplete streams; public request fingerprints and failure categories make attempts inspectable.

The preregistered four episodes all failed before an environment action: two HTTP 401 responses and two non-text stream-part rejections. They remain in the denominator. Read-only local inspection found native session sharing disabled; a later single GLM constant-output diagnostic passed but did not reproduce the full-input failure. Do not label this route live-validated, infer task weakness, silently enable shared authentication, or add permissive parser fallbacks.

**Gate carried into 2.4:** verify authentication for the actual endpoint before drawing evaluation cases; capture only reviewed structural event metadata in a separate diagnostic; resolve protocol compatibility with positive and negative fixtures; then publish a new fixed multi-turn plan. Preserve the plan, source commit and outcomes. A portable HTTP adapter does not imply that every subscription router implements its contract.

### P1.8 — Correct the contract, retain the remaining failures

**2.4 protocol corrections delivered; the all-four live gate remains failed.** The [independent follow-up](../studies/direct-channel-validation-v2/README.md) removes three incidental requirements: no reasoning content parts, mandatory repeated media headers, and mandatory repeated answers in the terminal envelope. It retains typed item ownership, whole-response completion, a single unambiguous assistant action and tool rejection. Native authentication is scoped to the current client's requests.

Both models completed their cascade task; the other two attempts failed after one action, through a stream failure/incomplete event and a fixed request deadline. All four replay; 19 requests yielded 17 complete usage reports. Changed private cases, harness and time limits prohibit interpreting the difference from 2.3 as a measured causal gain.

**Stop adding private cases to debug the endpoint.** The remaining transport investigation should use a bounded public-history probe and narrowly allowlisted error metadata, with no scoring or outcome-dependent retry. Preserve known-good protocol fixtures. Large P2 collection remains gated on adequate channel reliability and observable target failures. P3's offline measurement work can proceed independently.

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

**P3.1 delivered as an offline prototype:** [the versioned contract](DISCOVERY_RECOVERY.md)
implements one unknown dependency and an operation revealed by probing. A single
announced replacement after the first PASS invalidates the old handle, completed
work and verification. [All 60 public control trajectories](../studies/discovery-recovery-v1/README.md)
replay under the same 12-point/20-step limits. The adaptive witness succeeds in
all four ablations; static execution is rescued by visible/stable state, and
discovery without revision is rescued by removing replacement. Premature finish
and over-investigation fail throughout. A separate public-history acceptance
check agrees with the state grader. This closes the minimal contract/control gate,
not P3, model readiness, arbitrary hypothesis discovery or external validity.

**P3.2 implemented in 2.5:** `dependency-cover/1` combines hidden coverage,
overlapping alternatives, global work constraints and selective invalidation.
Four structural scales, an exact public-information reference, two competent
local heuristics and recovery/budget ablations use the shared collector and
replay. Diagnostic metrics remain null where inapplicable. Batch operations
remove unnecessary request overhead while preserving work cost. The
[192-episode development matrix and frozen model pilot](../studies/coverage-calibration-v1/README.md)
separate structural evidence from measured model difficulty.

**P3.3 next gate:** calibrate headroom against strong model/compute configurations,
then freeze private seeds and useful structural holdouts. Do not call larger
profiles frontier-hard before measurement. If the top scale saturates, design a
new version with overlapping anchors; if failures are transport-dominated, repair
the public-input channel gate before expanding private evaluation. Do not add
domains, scheduling, a plugin framework or a new overall score.

**Current evidence and next implementation:** the [completed follow-up](../studies/coverage-calibration-v2/README.md)
records Sol succeeding at the released top scale on one public seed; GLM's
corresponding attempt is censored by a transport-size limit. The default remains
unchanged, with an explicitly configurable allowance and boundary tests in 2.5.2.
The [180-call solver screen](../studies/coverage-search-v1/README.md) finds that the
released eight-build tasks remain easy for exact search. Candidate 18/24-build
structures are exploratory. Next, check their bounded reference runtime and
recovery ablations, freeze useful candidates and structural holdouts, and compare
direct-model and solver-assisted configurations under declared compute budgets.
Do not promote them solely because this reference exhausts a screening limit.

**P3.3a completed in 2.5.3:** [bounded candidate qualification](../studies/coverage-qualification-v1/README.md)
retains 252 planned rows, with 232 executed/replayed and 20 explicitly unavailable
prerequisites. The 72/4/216 and 96/4/288 structures pass complete reference,
heuristic and recovery/budget-rescue checks on all 12 public seeds. The 96/4/384
structure does not: 10 initial searches exceed the one-million-state limit.
The optimized exact-capacity path preserves all 180 earlier outcomes, state
counts and selected plans while removing repeated row scans.

**P3.3b implemented in 2.6:** freeze the two passing streams as experimental
`dependency-cover-depth/1` and reuse the same collector. Add a model-chosen solve
action with public-data-only inputs, finite calls and deterministic search effort.
Old anchors remain unchanged. A fixed tool-consumer script completes all 24
qualified cases, exposing how much this structure depends on unaided search.
The [four-attempt plan](../studies/coverage-depth-v1/README.md) declares direct and
assisted strong-model configurations before requests, and reserves two untuned
parameter combinations. They are not independent task families.

**P3.3b public pilot completed:** all four attempts replay; both open next-action
requests after probing hit their 600-second deadline, while both assisted
configurations complete with the fixed 9-action/2-call sequence. Keep the failed
deliveries and censored capability evidence. Twenty of 22 requests provide usage.
This does not pass a model-discrimination gate or identify a causal rescue.

**P3.3c next, in order:**

1. Test losslessly reconstructable public history to remove repeated observation/
   catalogue payloads. Assisted input totals were 405,648 and 468,256 tokens;
   compression savings and behavioral equivalence have not yet been measured.
   Preserve old encodings, replay and source bindings; freeze any new model check.
2. Retain coverage as an auditable search/tool-use control. Prototype a constrained
   information-acquisition problem where useful solvers still leave consequential
   choices. Current all-row probing and announced changes admit a fixed workflow.
3. Require a public-information witness, competent tool-equipped baselines and
   rescue ablations before model calls. Do not raise catalogue size or deadlines
   merely to force an apparent ranking. Reserved parameter combinations are not
   mandatory future expansions; private discrimination and real-work gates remain
   open. Preserve the third candidate's distribution for a separate reference study.

## P4 — Test whether the benchmark predicts real outcomes

Freeze an externally scored sample of real delegated tasks and a rubric for acceptance and human intervention time. Score benchmark configurations before revealing those outcomes. Compare prediction with static domain-skill and simple cost baselines; hold out task sources, not merely repeated runs.

**Deliverables:** consent/privacy-reviewed data protocol, preregistered analysis, task-level uncertainty, baseline comparisons and a report including null results.

**Exit gate:** useful prospective prediction beyond the baselines, or an explicit negative result narrowing the benchmark's purpose. Synthetic differences alone cannot close this gate. Do not substitute a simulator's hypothetical intervention count for measured human time.

## P5 — Accelerate and automate what survived the earlier gates

Profile actual collection, replay, analysis and maintenance costs. Remove avoidable recomputation before introducing parallel scheduling. Add concurrency only with endpoint rate limits, fair scheduling, interruption tests and immutable attempt accounting. Add family plugins only after two independent implementations expose a stable shared interface. Add recurring evaluation only when version drift and alert criteria are defined.

**Exit gate:** documented before/after cost or latency, unchanged measurement semantics, fault tests, and a named maintenance owner. Remove automation that produces noise rather than a decision.

## Evidence and dataset lifecycle

Public development seeds support debugging; private evaluation seeds support prospective collection; held-out structures test a different generalization claim. Retire and publish reviewed manifests/traces with versioned sources and exclusions. Never silently change a released study or erase failed collection attempts. New seeds alone do not establish contamination resistance.

The next gate is **P3.3's measured model headroom and frozen discrimination protocol**,
after the P3.2 structural generator/shared evidence implementation. Apply the
removal rule to each proposed source of difficulty. Keep endpoint diagnosis as a bounded public-input
activity; the 2.4 live gate remains failed despite two complete tasks. Do not expand
the completed pilots or infer model mechanisms from their execution failures.
Neither transport corrections nor a new synthetic structure close P2's mechanism
gate or P4's external-validity gate.
