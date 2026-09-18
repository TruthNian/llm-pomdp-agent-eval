# Research roadmap and acceptance gates

The implemented v2 framework is the measurement kernel. Growth is judged by additional validated constructs, not by the number of task descriptions or model names.

## Delivered in 2.0

- Versioned generation of heterogeneous diagnostic graphs and sequential revelation.
- Reliable and noisy evidence, heterogeneous costs, repair side effects and rollback.
- Public-information reference policy and three negative/control policies.
- Revision-aware verification, explicit finish, operational and step budgets.
- Provider-neutral named agents and a credential-separated HTTP adapter.
- Replay, source fingerprints, complete factorial-matrix checks, matched statistics and seed clustering.
- Frozen historical data, explicit historical validity notes, and cross-platform CI.

## Next: isolate the control mechanisms

Implement separate interventions for budget reservation, stopping, candidate-state memory and verification. A bundled procedural prompt cannot identify which mechanism caused an improvement.

Acceptance: predeclared factorial/ablation design; identical task and noise seeds across interventions; multiple models; enough independent generator seeds for useful uncertainty; all runs, including failures, published. Report interaction effects and saturation rather than ranking a model from a few examples.

## Next: genuinely different task structure

Add at least one environment where the agent must discover possible hypotheses or action dependencies, rather than receiving an exhaustive diagnostic catalogue. Candidate directions include a generated repository-debugging task with executable tests, a data-lineage investigation with causal interventions, and a research task whose evidence changes which question is worth pursuing.

Acceptance: executable public observation contract; agent-independent grader; reference or constructive solvability witness that does not read hidden state; known failure strategies; environment isolation; a written account of the new construct. A semantic reskin alone cannot satisfy this gate.

## Next: recovery as a primary challenge

Current wrong repairs are reversible, but the positive reference does not need to make mistakes. Add controlled misleading evidence, reversible probes, exogenous changes and repair prerequisites so recovery and belief revision are needed on successful paths.

Acceptance: distinguish rational exploration from error; score hindsight-independent action choices against the information available then; ensure both excessive caution and premature action can be suboptimal. Avoid rewarding a universal “stop after two clues” rule.

## Next: transfer and predictive validity

Collect a frozen, externally scored set of real delegated tasks with observed acceptance and human intervention time. Evaluate model configurations on the synthetic suite before looking at external outcomes. Compare prediction against static task skill and simple cost baselines.

Acceptance: held-out external tasks, confidence intervals over tasks rather than only repeated calls, declared harness and budgets, preregistered analysis, and honest negative results. Until this study exists, do not advertise synthetic scores as validated deployment forecasts.

## Next: durable evaluation operations

Add checkpoint-aware provider metadata, explicit retry policy, resumable collection with an append-only schedule, privacy-reviewed exports, and separately versioned task-family plugins. Keep resume semantics strict: completed episodes cannot be silently replaced.

Acceptance: interruption/recovery tests, exact matrix reconciliation, failed-request token accounting, no hidden configuration fallback, no secret-bearing artifacts, and stable reproducibility documentation.

## Dataset lifecycle and version governance

1. Public development seeds and reference policies support debugging.
2. Private evaluation seeds prevent exact-instance exposure during collection.
3. Predeclared held-out structures test generalization beyond random numbers.
4. On retirement, publish manifests, traces, source hashes, generation version and collection exclusions.
5. A new score-affecting generator or grader becomes a new version. Preserve previous results and label migration breaks.

Hidden seeds cannot make a public generator contamination-proof. If a model learns a general solution policy, that may be legitimate progress; if performance collapses on new structures, the metric must reveal that limitation. Independent family authors and external validation help distinguish the two.
