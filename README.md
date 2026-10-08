# POMDP Agent Benchmark

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Design](docs/DESIGN.md) · [Connect a model](docs/MODEL_ADAPTERS.md)

Test whether a model can independently investigate and resolve an unfamiliar operational incident, preserve business records and fulfil customer work. One test is a complete interaction, with normal tools, sparse handover, actual consequences and independent outcome checks.

**Current path: one incident, one agent, one result.** Framework 2.17 adds `stream-recovery/2`, reusing the existing isolated PostgreSQL/Kafka environment and collector. A fixed customer cohort retries identical commands. Acceptance follows every requested intent, including work that never obtained a successful HTTP receipt. Correct order state and external dispatches must survive restart.

```bash
python -m pip install -e .
python -m pomdp_bench benchmark --agent examples/benchmark-agent.example.json --runtime-config runtime.json --out artifacts/incident-test-001
python -m pomdp_bench validate artifacts/incident-test-001
```

Configure the model ID and existing endpoint/credential environment variables in the example. `runtime.json` is the pinned Docker configuration from the [stream runtime setup](docs/STREAM_RECOVERY.md#run-locally); an existing stream image can be reused. The [current contract](docs/STREAM_RECOVERY.md#customer-delivery-version-2) documents the customer policy and migration.

The run writes `result.md` and `result.json`, plus the complete trace and independent audit. Read the business outcome first, then token usage, elapsed time and verified expense where available. Background write-failure counts are diagnostic events; actions are an internal budget. Missing usage or expense remains unknown. Transport interruptions are reported separately from completed business failures. Existing failed runs are never silently retried.

This is a constructed operational benchmark. Difficulty must be measured from complete model behavior; a strong-model success remains useful evidence. The new acceptance is not a claim of frontier difficulty or broad production validity.

The [latest complete acceptance](studies/stream-delivery-completion-v1/README.md) passed: GPT-6 Astra `max` handed over all 12 customer intents, with 84 orders and 60 dispatches correct after restart. All 17 requests reported usage, totaling 656,034 tokens; expense is unknown. Three preceding interruptions and real operation controls remain separately retained. Version 2.17.3 provides bounded transport recovery, non-action metadata compatibility and complete-call checks. This success does not establish frontier difficulty or replace any previous grade.

[Previous model comparisons](docs/MODEL_COMPARISON_2026-09-24.zh-CN.md) and all versioned studies remain available. The historical families below are regression and research controls, outside the default single-test path.

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
grader source. Historical explicit-verification families expire a pass after an edit;
incident takeover instead grades business outcomes independently after handover. Failed attempts remain in the
denominator; missing usage remains unknown.

## Other task families

Python 3.11+; the evaluator uses the standard library. Repository repair additionally
requires Linux Docker containers. Its [run instructions](docs/REPOSITORY_REPAIR.md#run),
[controls](studies/repository-repair-v1/README.md) and
[three-task portfolio](studies/repository-portfolio-v1/README.md) remain available.
`validate` regrades recorded behavior; `recheck` executes the same actions again.
Credentials stay in environment variables and HTTP headers. Completed/interrupted
attempts are never silently replaced.

Without Docker or model credentials, run synthetic regression controls:

```bash
python -m pomdp_bench demo --out artifacts/demo --count 3
python -m pomdp_bench validate artifacts/demo
```

## Development and results

Apply **question → delete → simplify/optimize → accelerate → automate**.

- Make complete investigation, recovery and useful delivery the mainline.
- Keep synthetic diagnosis, discovery and coverage as controls.
- Remove catalogue growth and history compression as prerequisites for real work.
- Reuse collection, HTTP adapters and evidence checks.
- Build difficult tasks around evidence, compatibility and recovery constraints;
  calibrate against strong models while preserving immutable anchors.

The [staged roadmap](docs/ROADMAP.md) defines deliverables and removal conditions.
Report accepted delivery, intermediate business damage, actions, wall time, usage
and execution failures separately. Service runs cluster by incident scenario;
repair attempts by source task; synthetic runs by seed. Repeating one incident
does not create independent tasks.
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
on one public case. A fixed tool-consumer solved all 24 qualified cases. Coverage
therefore remains a search/tool-use control.

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
