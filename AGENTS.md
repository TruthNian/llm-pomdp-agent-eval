# Repository working contract

The project's objective is a durable evaluation framework for agents acting under partial observability. Specific model comparisons are versioned studies, not the project's identity.

## Preserve the measurement

- Read `docs/DESIGN.md` and `docs/SPECIFICATION.md` before changing environment semantics.
- Agents receive only the public observation projection. Do not expose private seeds, answers, case IDs, future catalogues, evaluator files or grading state.
- A solvability reference must use the public observation history. Label clairvoyant bounds separately.
- Successful verification is tied to the latest state revision and explicit handover.
- Count failures and incomplete matrices honestly. Never drop failed episodes, invent missing usage, or replace a failed run silently.
- New random seeds, repeated model runs, and semantic skins are distinct units. Keep paired design and seed clustering intact.
- New capabilities need executable positive/negative controls and a precise claim about the construct measured.
- Fresh seeds do not establish contamination resistance or real-world predictive validity.

## Preserve history

`harness/`, `results/`, `reports/`, and the three legacy documents listed in `studies/2026-gpt56-glm53/manifest.sha256.json` are frozen. Add errata beside a study; do not silently rewrite its data or methods. New generator, prompt or grader semantics need explicit versioning and migration notes.

## Verify useful behavior

Run the relevant state-machine and adapter tests. Before publishing changes, run the full unittest suite, `tools/verify_study.py`, `tools/verify_release.py`, `tools/check_docs.py`, and an offline `demo` followed by `validate`. Network model calls are separate from offline tests; report whether an integration was validated with a local fixture or a real provider.

Keep private manifests, generated suites, raw provider bodies and credentials out of Git. Use `artifacts/` for local runs. Use HTTPS Git remotes and the authenticated `gh` CLI for GitHub operations; never print authentication tokens.
