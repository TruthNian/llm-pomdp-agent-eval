# POMDP Agent Benchmark

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Design](docs/DESIGN.md) · [Connect a model](docs/MODEL_ADAPTERS.md)

Evaluate whether an agent can turn incomplete information into an **accepted,
useful outcome** under resource constraints. The unit is a complete interaction
trajectory, including unsuccessful actions, execution failures and delivery costs.

**The mainline is complete open incident response.** The [settlement incident](docs/SERVICE_INCIDENT.md)
executes actual HTTP requests and persists orders, an outbox and a ledger. An agent takes over an
ambiguous fault, investigates, acts, receives feedback, recovers backlog and reconciles accounts.
Temporary excess debits remain visible even when the final state is repaired.

This is a constructed local business system, not a claimed production incident. Difficulty needs
complete strong-model trajectories. Localized one-shot patch screens are no longer the mainline;
the three 2.8 source repairs and all historical evidence remain regression anchors.

```bash
python -m pip install -e .
python studies/settlement-incident-v1/controls.py artifacts/incident-controls
python -m pomdp_bench validate artifacts/incident-controls
```

No Docker is needed for this service task. Models operate trusted services through maintenance
interfaces; model-generated code never executes on the host. [Roadmap](docs/ROADMAP.md).

## Architecture

```text
Incident goal + acceptance contract
  → public observation → model action → real service operation
  → HTTP/SQL result + changed business state → next model decision
  → investigation / recovery / verification → explicit handover
  → complete trajectory + business outcome + accumulated harm
```

All families share one collector. Source, runtime, budgets and attempts bind to
evidence. Models receive public tool results, not manifests, upstream fixes or
grader source. Every edit expires verification. Failed attempts remain in the
denominator; missing usage remains unknown.

## Run

Python 3.11+; the evaluator uses the standard library. Real code execution
additionally requires Linux Docker containers.

```bash
python -m pip install -e .
docker pull python:3.13-slim
IMAGE=$(docker image inspect python:3.13-slim --format '{{.Id}}')
python studies/repository-repair-v1/controls.py --image "$IMAGE" --out artifacts/repair-controls
python -m pomdp_bench validate artifacts/repair-controls
```

[Six fixed controls](studies/repository-repair-v1/README.md) check correct repair,
unchanged code, an example-only fix, stale verification, test tampering and an
empty exit-zero process. The upstream repair is an artifact control, not a model
score. The command also re-executes checks in fresh containers.

`validate` regrades recorded behavior without candidate execution.
`recheck` explicitly executes again using the pinned image.
[Prepare a model run](docs/REPOSITORY_REPAIR.md#run) with named `chat` or
`responses` configurations. Credentials stay in environment variables and HTTP
headers. Completed/interrupted attempts are never silently replaced.

Without Docker or model credentials, run synthetic regression controls:

```bash
python -m pomdp_bench demo --out artifacts/demo --count 3
python -m pomdp_bench validate artifacts/demo
```

## Development and results

Apply **question → delete → simplify/optimize → accelerate → automate**.

- Make actual repair delivery and regression protection the mainline.
- Keep synthetic diagnosis, discovery and coverage as controls.
- Remove catalogue growth and history compression as prerequisites for real work.
- Reuse collection, HTTP adapters and evidence checks.
- Build difficult tasks around cross-file diagnosis, compatibility and recovery;
  calibrate against strong models while preserving immutable anchors.

The [staged roadmap](docs/ROADMAP.md) defines deliverables and removal conditions.
Report accepted patches, action/check counts, edited files, wall time, usage and
execution failures separately. Repeated repair attempts cluster by source task;
synthetic runs cluster by seed. One public issue is one independent task.
Human supervision time is reported only when measured. There is no default
weighted intelligence score.

## Preserved evidence

Published studies retain their original scope and failures:

- [Original GPT/GLM comparison and errata](studies/2026-gpt56-glm53/README.md).
- [v2 controls](studies/framework-v2-validation/README.md),
  [collection validation](studies/framework-v21-validation/README.md),
  [reminder pilot](studies/verification-reserve-pilot-v1/README.md).
- Direct-channel validation [v1](studies/direct-channel-validation-v1/README.md),
  [v2](studies/direct-channel-validation-v2/README.md).
- [Discovery/recovery](studies/discovery-recovery-v1/README.md),
  coverage calibration [v1](studies/coverage-calibration-v1/README.md),
  [v2](studies/coverage-calibration-v2/README.md),
  [search screen](studies/coverage-search-v1/README.md),
  [qualification](studies/coverage-qualification-v1/README.md),
  [depth/solver pilot](studies/coverage-depth-v1/README.md).

The depth pilot retained two open request timeouts and two assisted successes
on one public case. A fixed tool-consumer solved all 24 qualified cases. This
supports keeping coverage as a search/tool-use control while moving to actual
code delivery.

## Verify and contribute

```bash
python -m unittest discover -s tests -v
python tools/verify_study.py
python tools/verify_release.py
python tools/check_docs.py
```

[pomdp_bench/](pomdp_bench/) contains environments, adapters, collection and replay;
[docs/](docs/) defines contracts; [studies/](studies/) preserves evidence.
`harness/`, `results/` and `reports/` are frozen historical material.

[Contributing](CONTRIBUTING.md) · [Isolation](SECURITY.md) ·
[Changelog](CHANGELOG.md) · [Citation](CITATION.cff) · [Related work](docs/RELATED_WORK.md)

Project code and docs use [Apache-2.0](LICENSE). Bundled source snapshots retain
their [upstream licenses](pomdp_bench/repair_data/README.md).
This independent project has no provider affiliation or endorsement.
