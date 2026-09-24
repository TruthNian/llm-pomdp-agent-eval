# POMDP Agent Benchmark

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Design](docs/DESIGN.md) · [Connect a model](docs/MODEL_ADAPTERS.md)

**Stage review:** [2026-09-23 acceptance record (中文)](docs/ACCEPTANCE_2026-09-23.md).
That record preserves the stage-review state at the time. The execution and measurement loop works;
the high-difficulty objective remains unmet.
The [three user-requested model tests](studies/stream-recovery-requested-models-v1/README.md) have ended:
GPT-6 Sol delivered in 27 actions; GPT-6 Luna handed over in 28 but left twelve orders and nine dispatches
missing. GLM's native-tool attempt failed at the interface; its separate text follow-up timed out on
request ten. All four attempts remain retained. In a later user-directed,
[separately frozen normal-runtime pilot](studies/stream-recovery-codex-native-glm-v1/README.md),
GLM completed 37 actions and handed over, but independent grading found twelve wrong orders and
nine missing dispatches. That pilot measures GLM through Codex and the local router under a different
interface and reasoning setting; it does not establish a strict model ranking. No new frontier
scenario was added in that integration work.

Evaluate whether an agent can turn incomplete information into an **accepted,
useful outcome** under resource constraints. The unit is a complete interaction
trajectory, including unsuccessful actions, execution failures and delivery costs.

**The mainline is sparse incident takeover.** The [2.13 PostgreSQL candidate](docs/POSTGRES_TAKEOVER.md)
uses a generic shell, actual divergent database timelines, continuing customer traffic and independent
business grading. No evaluator verification command or incident-specific operation menu is provided.
The [completed native-tool screen](studies/incident-takeover-native-v1/README.md) delivered in
9/150 actions: all 110 accepted orders survived, including restart. This candidate is rejected as
high-difficulty evidence. Seventeen reads and seventeen writes failed during permitted maintenance;
those costs remain visible. Earlier [text-channel failures](studies/incident-takeover-v1/README.md)
are retained separately. The high-difficulty objective remains unmet.

The [2.15 destructive recovery study](studies/stream-recovery-v1/README.md) now retains four
real mechanism controls and a complete Sol max attempt: 29 actions, twelve unrecovered orders
and nine missing dispatches, without protocol or observer errors. Its stateless history adapter
does not preserve native reasoning continuity, so this is not yet a continuous-agent ceiling result.
The [matched artifact experiment](studies/stream-recovery-counterfactual-v1/README.md) now confirms
that recovering missing history removes both deficits without replacing the model's repaired pipeline.
The separately frozen [continuous native-session screen](studies/stream-recovery-continuous-v1/README.md)
delivered in 31/200 actions: all 111 accepted orders and 93 required dispatches passed after restart.
Maintenance refused 128 customer writes. Reject this candidate as high-difficulty evidence and retain
it as a regression anchor. These unpaired attempts do not isolate the adapter's causal effect.

The earlier [settlement incident](docs/SERVICE_INCIDENT.md)
executes actual HTTP requests and persists orders, an outbox and a ledger. An agent takes over an
ambiguous fault, investigates, acts, receives feedback, recovers backlog and reconciles accounts.
Temporary excess debits remain visible even when the final state is repaired.

This is a constructed local business system, not a claimed production incident. Difficulty needs
complete strong-model trajectories. Localized one-shot patch screens are no longer the mainline;
the three 2.8 source repairs and all historical evidence remain regression anchors.

```bash
python -m pip install -e .
python studies/stream-recovery-continuous-v1/verify.py
```

This regrades the published complete run without Docker or model calls. Read its
[full action trace](studies/stream-recovery-continuous-v1/trajectories.html), or follow the
[Docker setup and native-model run instructions](docs/POSTGRES_TAKEOVER.md#run-locally)
for a fresh incident. Candidate shell/Python runs inside the isolated Linux container.
The older HTTP/SQLite service tasks remain available as regression anchors.

[Complete live trajectories and evidence](studies/settlement-incident-v1/README.md):
Sol delivered in 20 actions. The original GLM attempt stopped at the old parser after
13 actions; this is not evidence of cognitive difficulty. Both outcomes and their
intermediate business consequences are retained, with matching fresh execution.
This scenario is a workflow anchor; the required frontier difficulty is not yet achieved.

A separately frozen [GLM follow-up](studies/settlement-incident-v2/README.md)
completed in 26 actions, including recovery from two malformed action responses.
All 33 accepted orders reconciled. The original failed attempt remains published;
the two adapter versions are not pooled into a model ranking.

Framework 2.11 adds [cross-component reconciliation repair](docs/RECONCILIATION_REPAIR.md): actual SQL edits, intermediate execution, deployment and historical recovery across two financial feed contracts. [Complete evidence](studies/reconciliation-repair-v1/README.md) retains thirteen controls and both interrupted Sol max attempts. An unchanged model patch passes a separate scripted probe check; neither live attempt completed, and high difficulty remains unproven.

The separately frozen [network-recovery follow-up](studies/reconciliation-repair-v2/README.md) completed both contracts in 28 actions, without invalid actions or transport errors. Keep these as regression anchors; high difficulty was not demonstrated. The [2.12 refund screen](studies/refund-recovery-v1/README.md) also passed: Sol max delivered in 39/100 actions. This candidate is rejected as high-difficulty evidence; further miniature SQL variants are no longer the frontier mainline.

Framework 2.10 adds [external settlement](docs/EXTERNAL_SETTLEMENT.md): separate provider/local state, finite refund liquidity, cancellation deadlines and delayed notifications. Local bookkeeping cannot undo an external payment. [Complete evidence](studies/external-settlement-v1/README.md): Sol delivered in 26 actions; the GLM route timed out on request 10 after nine actions. Seven mechanism controls separated as specified. The configuration-invariance check failed and remains disclosed; this is integration evidence, not a controlled model comparison or proof of frontier difficulty.

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
