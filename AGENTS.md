# Repository working contract

The project's objective is a durable, difficult evaluation of agents delivering useful outcomes under partial observability. The development mainline is a complete open interaction: investigate, act, observe consequences, recover and verify the real business state. Executable service incidents currently implement this loop. Repository repair fixtures and synthetic tasks remain useful component controls. Specific model comparisons are versioned studies, not the project's identity.

Question requirements, delete unnecessary dependencies, then simplify and optimize before accelerating or automating. Preserve the information/action/feedback loop when simplifying. Do not substitute localized one-shot answers, CI counts or release counts for complete model trajectories. Follow `docs/ROADMAP.md`.

## Preserve the measurement

- Read `docs/DESIGN.md` and `docs/SPECIFICATION.md` before changing environment semantics.
- Agents receive only the public observation projection. Do not expose private seeds, answers, case IDs, future catalogues, evaluator files or grading state.
- A solvability reference must use the public observation history. Label clairvoyant bounds separately.
- Successful verification is tied to the latest state revision and explicit handover.
- Count failures and incomplete matrices honestly. Never drop failed episodes, invent missing usage, or replace a failed run silently.
- Distinguish planned, executed and unexecuted controls. Missing prerequisites have no observed outcome; do not invent successes/failures or claim every planned row ran. An offline qualification pass is not model-discrimination evidence.
- New random seeds, repeated model runs, and semantic skins are distinct units. Keep paired design and seed clustering intact.
- New capabilities need executable positive/negative controls and a precise claim about the construct measured.
- Execute candidate code only in the declared isolated runtime. Preserve source/runtime identities, behavioral outputs and patches. Distinguish recorded-behavior replay from fresh execution. An upstream fix is an artifact control, never an observation-only policy or model score.
- Fresh seeds do not establish contamination resistance or real-world predictive validity.
- High, adjustable and empirically discriminating difficulty is a core requirement. Do not infer it from task length, profile names, or failure of a deliberately weak policy. Keep a solvable public-information reference, competent heuristics, rescue ablations and explicit ceiling/floor checks on strong model configurations.
- Preserve versioned difficulty anchors. Calibrate new scales before claiming frontier headroom; infrastructure failures do not demonstrate cognitive difficulty. Do not alter a frozen matrix or its budgets after observing model results.

## Preserve history

`harness/`, `results/`, `reports/`, and the three legacy documents listed in `studies/2026-gpt56-glm53/manifest.sha256.json` are frozen. Add errata beside a study; do not silently rewrite its data or methods. New generator, prompt or grader semantics need explicit versioning and migration notes.

## Verify useful behavior

Run the relevant state-machine and adapter tests. Before publishing changes, run the full unittest suite, `tools/verify_study.py`, `tools/verify_release.py`, `tools/check_docs.py`, and an offline `demo` followed by `validate`. Network model calls are separate from offline tests; report whether an integration was validated with a local fixture or a real provider.

Keep private manifests, generated suites, raw provider bodies and credentials out of Git. Use `artifacts/` for local runs. Use HTTPS Git remotes and the authenticated `gh` CLI for GitHub operations; never print authentication tokens.
