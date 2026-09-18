# POMDP Agent Benchmark

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[中文](README.zh-CN.md) · [Design](docs/DESIGN.md) · [Specification](docs/SPECIFICATION.md) · [Connect a model](docs/MODEL_ADAPTERS.md)

An open framework for evaluating how agents **discover information, make decisions, preserve resources, recover from mistakes, and verify outcomes** when the full problem is unavailable at the start.

The unit of evaluation is an interaction trajectory. Actions reveal evidence, change the world, and consume future options. Successful completion must correspond to an accepted environment state.

**Version 2.0 is a working generative research framework.** It includes two related diagnostic task families, public-observation reference policies, provider-neutral model access, deterministic replay, and failure-inclusive reporting. Its relationship to real-work performance remains an empirical question; no new frontier-model ranking is claimed. The original 72-run GPT/GLM comparison is preserved as a [historical study](studies/2026-gpt56-glm53/README.md).

## Run without an API key

Python 3.11+; no runtime dependencies. From the repository root:

```bash
python -m pomdp_bench demo --out artifacts/demo
python -m pomdp_bench validate artifacts/demo
```

Four scripted policies receive the same generated cases:

| Policy | Information available | Purpose |
|---|---|---|
| `reference` | Public observations only | Positive control: minimax reliable-test tree, repair, verify, finish |
| `random` | Public action catalogue | Chance/action-selection baseline |
| `overdiagnose` | Public observations only | Negative control: run the entire diagnostic checklist twice |
| `proxy` | Public observations only | Negative control: force the dashboard green and finish |

The reference is optimal within its restricted class of reliable diagnostic trees. The scorer's clairvoyant action-cost lower bound is recorded separately and is never presented as a fair agent baseline.

Output contains `summary.json` plus a `private/` manifest and traces. Validation regenerates every case, replays every transition, recomputes grades, and rejects missing or duplicate episodes. Existing run directories are never overwritten. Keep private files inaccessible to evaluated agents.

Optional installation: `python -m pip install -e .` provides the `pomdp-bench` command.

## Generate a new evaluation

```bash
python -m pomdp_bench generate --fresh --count 24 --families diagnosis cascade --profiles standard wide deep --out artifacts/private/suite.json
python -m pomdp_bench run --suite artifacts/private/suite.json --agents examples/agents.json --conditions open principles procedural --out artifacts/controls
python -m pomdp_bench validate artifacts/controls
```

Use `--seed 0` instead of `--fresh` for a reproducible **development** suite. Fresh generation randomizes hypotheses, test partitions, costs, test accuracy, catalogue order, hidden answers, and phase structure. Repeats vary observation noise; they do not create new independent tasks. `wide` and `deep` enable declared structural stress tests. Reserve profiles before tuning if using them as held-out conditions.

| Family | What the agent encounters | Main pressure |
|---|---|---|
| `diagnosis` | One unknown cause; cheap noisy tests and costlier reliable group tests | Information acquisition, stopping, resource allocation |
| `cascade` | Later diagnostic catalogues appear only after earlier repairs | Replanning, resetting outdated hypotheses, preserving future budget |

Wrong repairs cause reversible collateral damage. A dashboard override can show health while the true goal remains unmet. Verification expires after any mutation. Free, invalid, and blocked actions count toward a step limit.

`incident` and `data_pipeline` are **paired semantic skins of the same kernels**, not independent real-world domains. [Measurement boundaries](docs/DESIGN.md#measurement-boundaries).

## Connect future models

The runner accepts arbitrary named agents; scoring embeds no model names or two-model assumption. The built-in `chat` adapter speaks the common Chat Completions JSON format and sends only the public task, current observation, and observation/action history. It gives the model no shell, filesystem, manifest, seed, or grader access.

1. Copy [the example configuration](examples/chat-agent.example.json) and specify your model identifier and supported options.
2. Set `BENCH_CHAT_ENDPOINT` to the full HTTPS chat-completions endpoint and `BENCH_API_KEY` in your local environment.
3. Run the same suite and conditions using that configuration:

```bash
python -m pomdp_bench run --suite artifacts/private/suite.json --agents my-agents.json --conditions open principles procedural --replicates 3 --out artifacts/models
```

Calls incur normal provider usage. Credentials stay in environment variables and HTTP headers. Provider-specific reasoning settings must be explicitly supplied and reported; no hidden setting conversion or silent fallback occurs. See [adapter protocol and integration tests](docs/MODEL_ADAPTERS.md).

## Read the results

The primary endpoint is **accepted completion**: all phases resolved, collateral damage cleared, overrides off, successful verification of the latest state, and explicit termination within budgets.

Reports include:

- Success counts and rates by agent, condition, family, profile, and skin.
- Observed action cost and tokens per accepted completion, including unsuccessful attempts.
- Diagnostics after exact identification, wrong repairs, proxy attempts, and lost completion budget.
- Matched agent comparisons and procedural-minus-open prompt sensitivity.
- Seed-cluster bootstrap intervals that keep repeated runs and semantic skins together.
- Adapter failures in the denominator; missing usage represented as `null`.

There is no arbitrary composite intelligence score. Prompt sensitivity describes this intervention; it is not a validated intrinsic autonomy scale. Token counts do not imply equal compute or equal prices. [Metric definitions](docs/SPECIFICATION.md#metrics-and-comparison).

## Long-term research contract

The durable contribution is the **evaluation contract and evidence**, rather than a permanent ranking of specific model versions:

1. Version generators, observations, transitions, prompts, and graders.
2. Keep answer state and scoring outside the agent's observation boundary.
3. Validate solvability using an observation-limited policy.
4. Test cosmetic success and pathological strategies with negative controls.
5. Evaluate new structures as well as new random seeds.
6. Freeze studies; publish manifests and traces after their held-out lifecycle ends.
7. Validate transfer to real tasks before making deployment-performance claims.

Existing interactive benchmarks already address substantial parts of this problem. Our narrower contribution and comparison with AgentBoard, τ-bench, OSWorld, and InfoSeeker are in [related work](docs/RELATED_WORK.md). [The roadmap](docs/ROADMAP.md) gives evidence requirements for future extensions.

## Repository map

```text
pomdp_bench/    Generator, environment, policies, adapters, runner, replay, statistics
examples/       Offline policies and environment-variable-based model configuration
docs/           Specification, design, validity, extension and release contracts
tests/          Transitions, generation, leakage, replay, HTTP, data integrity
studies/        Historical study index and immutable file hashes
harness/        Frozen v1 implementation (historical reproduction only)
results/        Frozen v1 trajectories and derived data
reports/        Frozen v1 reports
```

Historical files retain their paths to preserve links and reproduce the original study. Their [known validity limitations](studies/2026-gpt56-glm53/ERRATA.md) are explicit; v2 scoring must not be silently applied to v1 data.

## Contribute and verify

```bash
python -m unittest discover -s tests -v
python tools/verify_release.py
python tools/verify_study.py
python -m pomdp_bench demo --out artifacts/check
python -m pomdp_bench validate artifacts/check
```

[Contributing](CONTRIBUTING.md) · [Isolation](SECURITY.md) · [Changelog](CHANGELOG.md) · [Citation](CITATION.cff)

Code, documentation, and released synthetic data are licensed under Apache-2.0. This independent project has no affiliation or endorsement from model providers.
