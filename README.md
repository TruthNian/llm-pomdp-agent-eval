# POMDP Agent Benchmark

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[中文](README.zh-CN.md) · [Design](docs/DESIGN.md) · [Specification](docs/SPECIFICATION.md) · [Connect a model](docs/MODEL_ADAPTERS.md)

An open framework for evaluating how agents **discover information, make decisions, preserve resources, recover from mistakes, and verify outcomes** when the full problem is unavailable at the start.

The unit of evaluation is an interaction trajectory. Actions reveal evidence, change the world, and consume future options. Successful completion must correspond to an accepted environment state.

**Version 2.5 adds a structural difficulty ladder and selective recovery.** Agents discover overlapping operations, plan under finite work allowances, and rebuild only invalidated goals. Four scales reach 48 goals and 96 alternatives. Exact public-information controls distinguish global planning from competent local heuristics; [strong-model calibration](studies/coverage-calibration-v1/README.md) is separate from this implementation evidence. Real-work validity remains unproven; the original 72-run comparison is a [historical study](studies/2026-gpt56-glm53/README.md).

High and discriminating difficulty is a [core maintenance contract](docs/DIFFICULTY.md): measure ceiling/floor effects, preserve immutable anchors, and version new scales as models improve. A larger task name or longer transcript does not establish difficulty.

**Calibration finding:** in the [completed follow-up](studies/coverage-calibration-v2/README.md),
Sol solved the current top scale on one public seed; GLM's corresponding run hit
a transport-size limit. Frontier headroom remains unproven. The
[reproducible solver screen](studies/coverage-search-v1/README.md) retains all 180
searches and investigates deeper combinations before promoting new scales.

The [2.5.3 candidate qualification](studies/coverage-qualification-v1/README.md)
retains 252 planned controls: 232 executed/replayed, 20 explicitly unavailable.
Two deeper structures pass the offline reference and rescue checks; the third
exhausts the reference budget on 10/12 seeds. None is yet model-calibrated.

**2.6 exposes the useful-tool test:** the two passing structures are explicitly
experimental depth18/depth24 profiles. An optional, limited solve action returns
plans from revealed data while leaving execution/recovery/verification to the
model. A fixed tool-consumer script solves all 24 qualified cases; broad
agent-difficulty claims therefore need a stronger construct. The
[four-attempt plan](studies/coverage-depth-v1/README.md) separates direct and
assisted configurations; tool compute is not treated as free model reasoning.

Development follows [explicit stages and acceptance gates](docs/ROADMAP.md): reliable collection → isolated intervention studies → new task structures → external validity → measured acceleration. Requirements are questioned, unnecessary work is removed, and the remaining workflow is simplified before it is automated. For long collections, use [`prepare`, `status` and `resume`](docs/COLLECTION.md); completed and interrupted attempts are never silently replaced.

For a single-intervention experiment, use [`prepare-study`](docs/STUDIES.md). The [offline example](examples/study-reserve.pilot.json) checks a deliberately budget-blind control, a successful reference and a failing cosmetic-status policy. Study analysis reports a reminder contrast within each agent; it does not automatically rank the models or turn a tiny perfect-success pilot into a precise population claim.

The [preregistered eight-episode live pilot](studies/verification-reserve-pilot-v1/README.md) is complete, including two retained bridge failures and a native capability-boundary limitation. It does not establish a reminder effect. The next gate is reliable action-channel isolation, before expanding collection.

The [first direct-channel validation](studies/direct-channel-validation-v1/README.md) retained four first-request failures. In the [independent 2.4 follow-up](studies/direct-channel-validation-v2/README.md), both models completed a cascade task; the other two attempts retained a stream failure and a timeout. **The all-four integration gate remains failed.** All attempts replay, and development probes do not replace earlier failures.

## Run without an API key

The next task structure now has a [versioned offline discovery/recovery prototype](docs/DISCOVERY_RECOVERY.md).
Its [60-trajectory control matrix](studies/discovery-recovery-v1/README.md) tests unavailable operations,
announced invalidation and rebuilding, with ablations that rescue the relevant failing controls.
It is not a registered scored family or evidence of model performance. Run and replay it separately:

```bash
python -m pomdp_bench.discovery_controls --out artifacts/discovery-controls.json
python -m pomdp_bench.discovery_controls --validate artifacts/discovery-controls.json
```

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

[Published implementation validation](studies/framework-v2-validation/README.md): 144 generated cases and 576 replayed episodes; reference 144/144, random 4/144, both negative controls 0/144. These are scripted controls, not model scores.

Output contains `summary.json` plus a `private/` manifest and traces. Validation regenerates every case, replays every transition, recomputes grades, and rejects missing or duplicate episodes. Existing run directories are never overwritten. Keep private files inaccessible to evaluated agents.

Optional installation: `python -m pip install -e .` provides the `pomdp-bench` command.

## Generate a new evaluation

For the planning/recovery ladder, use the same collector with a separate generator:

```bash
python -m pomdp_bench generate-cover --fresh --count 12 --scales sanity challenge hard extreme --out artifacts/private/cover.json
python -m pomdp_bench prepare --suite artifacts/private/cover.json --agents examples/coverage-agents.json --out artifacts/cover
python -m pomdp_bench resume artifacts/cover
python -m pomdp_bench validate artifacts/cover
```

Batch reads/builds preserve resource costs while removing unnecessary requests.
Use `--stable` or `--slack N` only as declared ablations. Scale names describe
structure; model headroom must be measured. [Rules, solvability and calibration gates](docs/DIFFICULTY.md).

The original diagnostic generator remains available with unchanged semantics:

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

The runner accepts arbitrary named agents; scoring embeds no model names or two-model assumption. The `chat` and `responses` adapters send only the public task, current observation, and observation/action history, with no tool dispatcher or native agent runtime. They provide no shell, filesystem, manifest, seed, or grader access. See the [Responses configuration](examples/responses-agent.example.json) for that protocol.

1. Copy [the example configuration](examples/chat-agent.example.json) and specify your model identifier and supported options.
2. Set `BENCH_CHAT_ENDPOINT` to the full HTTPS chat-completions endpoint and `BENCH_API_KEY` in your local environment.
3. Run the same suite and conditions using that configuration:

```bash
python -m pomdp_bench run --suite artifacts/private/suite.json --agents my-agents.json --conditions open principles procedural --replicates 3 --out artifacts/models
```

Calls incur normal provider usage. Credentials stay in environment variables and HTTP headers. Provider-specific reasoning settings must be explicitly supplied and reported; no hidden setting conversion or silent fallback occurs. See [adapter protocol and integration tests](docs/MODEL_ADAPTERS.md).

## Read the results

The primary endpoint is **accepted completion**: all phases resolved, collateral damage cleared, overrides off, successful verification of the latest state, and explicit termination within budgets.

Ordinary-run summaries include:

- Success counts and rates by agent, condition, family, profile, and skin.
- Observed action cost and tokens per accepted completion, including unsuccessful attempts.
- Diagnostics after exact identification, wrong repairs, proxy attempts, and lost completion budget.
- Matched agent comparisons and procedural-minus-open prompt sensitivity.
- Seed-cluster bootstrap intervals that keep repeated runs and semantic skins together.
- Adapter failures in the denominator; missing usage represented as `null`.

Preregistered studies use the plan-bound `study_analysis` as their primary analysis: seed-level simultaneous Hoeffding intervals and separate execution-censoring bounds. Generic bootstrap fields are descriptive compatibility outputs for these studies.

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
