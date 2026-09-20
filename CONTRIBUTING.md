# Contributing

Contributions should strengthen the validity and longevity of the evaluation: new decision structures, observable mechanism tests, reliable scoring, reproducible collection, and external-task validation. Read [the design](docs/DESIGN.md), [specification](docs/SPECIFICATION.md), and [acceptance gates](docs/ROADMAP.md) first.

## Development checks

The project uses the Python standard library. Before opening a pull request, run:

```bash
python -m compileall pomdp_bench harness tests tools
python -m unittest discover -s tests -v
python tools/verify_release.py
python tools/verify_study.py
python tools/check_docs.py
python -m pomdp_bench demo --out artifacts/contribution-check --count 4
python -m pomdp_bench validate artifacts/contribution-check
python -m pomdp_bench.discovery_controls --out artifacts/discovery-check.json
python -m pomdp_bench.discovery_controls --validate artifacts/discovery-check.json
python -m pomdp_bench.discovery_controls --validate studies/discovery-recovery-v1/controls.json
```

The v1 study is frozen. Recompute its statistics only for audit, without committing replacements:

```bash
python harness/analyze_results.py
```

## Experimental changes

Changes to prompts, costs, observation kernels, scoring, model options or timeout policy alter the experiment. Bump the appropriate generator/protocol/benchmark version, document migration, and add counterexample tests. Do not mix new trajectories with published studies.

New comparisons should remain balanced and paired across agents, conditions and replicates. Declare structural holdouts before tuning. Keep failed and interrupted collections visible; never rerun only failures and present the replacement as the original matrix.

## New task family

Describe the construct being measured and why an existing family cannot measure it. Provide a deterministic generator, explicit public/hidden schemas, transition/acceptance rules, a public-information solvability witness, designed negative controls, replay tests and an instance lifecycle. Additional prose around the same latent graph is a semantic control, not a new construct.

Do not claim global POMDP optimality for a restricted reference policy. Distinguish a clairvoyant lower bound from an observation-limited agent. Report what is known at each decision; hindsight alone does not make an action irrational.

## Data safety

Never commit:

- `runs/` directories;
- raw Codex JSONL event streams;
- bearer tokens or provider credentials;
- unrelated user data;
- model-readable copies of the simulator or answer key.
- private evaluation seeds or manifests before a suite is retired;
- provider API keys, credential-bearing URLs, or raw error bodies.

The repository `.gitignore` blocks the main transient artifacts, but contributors remain responsible for reviewing staged files.

## Pull requests

Describe:

1. the methodological or implementation change;
2. which experimental factors it affects;
3. tests performed;
4. whether released metrics change;
5. any new limitations introduced;
6. which evidence supports the claimed capability or construct;
7. whether any new network/model integration was tested live or only with a fixture.

By contributing, you agree that your contribution is licensed under Apache-2.0.
