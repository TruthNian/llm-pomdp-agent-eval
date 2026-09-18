# Verification reserve: preregistered feasibility pilot

**Status: all eight planned episodes collected and replayed; feasibility gate not passed.** The [machine-readable plan](plan.json) and bridge were published before model calls and remain unchanged. Results below are appended to that preregistration. GPT showed no observed baseline headroom; both GLM neutral-arm episodes were interrupted by the local execution channel. No confirmatory reminder effect is established.

本实验只检验一个提示差异：在同为 15 个英文词的中性说明与验证预算提醒之间，交付结果是否发生变化。先检查真实模型是否存在目标预算失败，再决定是否值得扩大实验。两个生成种子只支持探索性试跑，不支持总体效果确认。

## Prespecified design

- Two freshly generated independent private seeds, one diagnostic family, standard profile, incident skin and one replicate.
- Both `neutral_cost_v1` and `reserve_verify_v1` for each of GPT-5.6 Sol and the local `custom/z-ai/glm-5.3` registration: **eight episodes total**.
- Identical generator, observations, task acceptance and operational costs between arms; model reasoning requested at `high` in both arms.
- Adjacent condition pairs, counterbalanced first condition by seed/agent and rotated model order. No outcome-dependent stopping, retries, dropped failures or additional seeds.
- 180-second HTTP request limit; 150-second local bridge event wait; 900-second episode wall budget. All are declared before these model calls. These limits differ from the earlier integration check and are not pooled with it.
- Primary estimand: treatment-minus-neutral accepted completion, paired within case and averaged within seed, then equally across seeds, separately for each model.
- Minimum useful effect: 0.20 absolute success-rate difference. Target precision: 95% simultaneous confidence, half-width 0.10. The conservative confirmatory requirement is 877 independent seeds; this two-seed collection is explicitly a pilot.
- Report the fixed primary interval, execution-censoring identification bounds, and observed neutral-arm task/budget failures. Existing cross-model pairwise ranking is disabled for this study.

## Prespecified interpretation and stopping

Complete all eight scheduled entries unless the collector itself must stop; strict resume retains any interrupted failure. A provider error does not trigger a replacement. The fixed-matrix rule does not authorize enlarging this pilot after observing results.

If execution censoring occurs, resolve the transport limitation before capability interpretation. If the neutral arm has no observed task failures, record the lack of observed headroom. If task failures occur but no budget losses occur, reconsider the targeted failure. Only a pilot containing target failures motivates planning a larger experiment of this reminder. Any changed distribution, outcome or intervention needs a separately published plan.

No result identifies model training recipes or a unique internal reasoning mechanism. Equal word count is not equal provider token count, the neutral sentence may affect attention, and equal effort labels are not equal compute. The statistical interval assumes independent seed-level outcomes under stable serving; counterbalancing does not prove that assumption.

## Harness

Use the existing Python `chat` adapter and a loopback bridge to the operator's installed Codex app server. Each model action uses a fresh ephemeral context with complete public task history. Disable environment access, dynamic tools, shell, browser, apps, plugins and delegation. No private seed, answer, manifest or evaluator path enters model input. The runtime's generic GitHub-operation instructions remain an explicitly acknowledged additional context shared by both arms.

The exact [bridge source snapshot](bridge_snapshot.py.txt) is published with this plan before calls. Its fingerprint, observed configurations and all planned terminal outcomes will accompany the results. Raw provider reasoning, credentials and private evaluation manifests are not published. Native transport and provider checkpoint identities are not independently attested; failed-request billing and remote cancellation may remain unknown.

Methods and control definitions: [STUDIES.md](../../docs/STUDIES.md). Earlier transport behavior, including its retained timeout: [2.1 validation](../framework-v21-validation/README.md).

## Collected outcomes — 2026-09-18

The [preregistered commit](https://github.com/TruthNian/llm-pomdp-agent-eval/commit/ba10b37bb6cf913523714c5b71521f93c0f926eb) was received by GitHub's push workflow at 10:31:34 UTC. Preparation occurred at 10:31:56; the first episode started at 10:32:14. Collection used a clean checkout of that commit. All 13 core source fingerprints and the bridge snapshot match the published bytes. [Machine-readable evidence](evidence.json) includes the timestamps, exact fingerprints, all eight terminal outcomes, primary analysis and all 37 request statuses. Private seeds, manifests and full traces remain local; the public summary alone cannot replay the environments.

No episode was retried, replaced or dropped, and no seeds were added. The two private seed clusters are labeled A and B here; these labels do not reveal their values.

| Order | Cluster | Model | Condition | Accepted | Durable steps | Action cost / budget | Termination |
|---:|---|---|---|---|---:|---:|---|
| 1 | A | GPT-5.6 Sol | neutral | yes | 7 | 18 / 21 | explicit finish |
| 2 | A | GPT-5.6 Sol | reserve | yes | 6 | 14 / 21 | explicit finish |
| 3 | A | GLM-5.3 local registration | reserve | yes | 6 | 14 / 21 | explicit finish |
| 4 | A | GLM-5.3 local registration | neutral | no | 1 | 2 / 21 | unexpected `imageGeneration` item |
| 5 | B | GLM-5.3 local registration | neutral | no | 0 | 0 / 15 | local bridge event timeout |
| 6 | B | GLM-5.3 local registration | reserve | yes | 5 | 14 / 15 | explicit finish |
| 7 | B | GPT-5.6 Sol | reserve | yes | 5 | 14 / 15 | explicit finish |
| 8 | B | GPT-5.6 Sol | neutral | yes | 5 | 14 / 15 | explicit finish |

The bridge completed 35 requests and rejected two. Request 21 returned an unexpected completed item of type `imageGeneration`; request 22 exhausted the 150-second event wait. Both became local HTTP 502 responses. The trace's generic `Provider HTTP status 502` therefore does not establish an upstream provider 502. Failed-request usage is unknown; recorded earlier counters are partial evidence only. A separate successful request took 125.916 seconds, within the limit declared before collection. This demonstrates why an explicit request budget is useful, without showing that this budget eliminates interruption.

### Capability boundary correction

The published bridge disables environment access, dynamic tools and the listed shell/browser/app/plugin features, but **omits the independent `image_generation` feature switch**. A read-only feature check using the same overrides in the same empty workspace reported `image_generation ... true`. Consequently this pilot does not establish the intended tool-free action channel. The event type alone does not establish that an image was generated, or identify whether the model, router or runtime emitted it. The bridge rejected the event and retained the failure; that downstream rejection is not proof that all upstream capabilities were unavailable.

This limitation applies to the harness used by both arms. The original bridge snapshot is preserved, not silently corrected after collection. It is experimental evidence, not a supported portable adapter. Any future native-runtime pilot must first verify effective capabilities, including hosted generation tools, under a separately versioned bridge and plan. The regular provider-neutral HTTP adapter remains the supported benchmark interface.

### Preregistered analysis and decision

| Within-model contrast | Neutral accepted | Reserve accepted | Observed delivery difference | 95% simultaneous primary interval | Execution-censoring identification bounds | Pilot gate |
|---|---:|---:|---:|---|---|---|
| GPT-5.6 Sol | 2/2 | 2/2 | 0.00 | [-1, 1] | [0, 0] | no observed baseline headroom |
| GLM-5.3 local registration | 0/2 | 2/2 | +1.00 | [-1, 1] | [0, 1] | resolve execution censoring |

GLM's +1.00 is the failure-inclusive delivered-outcome contrast. Both neutral outcomes are censored by the execution channel, so it is **not evidence that the reminder rescued a budget-management failure**. The finite-sample identification range includes zero; the primary sampling interval covers the entire outcome-difference range. GPT's observed zero and [0,0] censoring bounds likewise do not establish population equivalence. The latter bounds only say that its observed sample has no execution-censored outcome.

Neither model had an observed task failure caused by budget loss. Both contrasts remain `exploratory_only`, with only two independent seeds against a declared conservative precision requirement of 877. No model ranking, unique internal mechanism, training explanation or real-work prediction is supported.

**Decision:** do not scale this experiment. Resolve and verify the native capability/transport boundary before another live study, then reconsider whether the task distribution exhibits the target failure. Publish a new plan for any changed harness or distribution; keep this complete negative feasibility result. Adding reminders, factors or calls now would not answer the blocked question.

## Implementation acceptance

- All 70 tests passed. The targeted control test replayed 576 episodes across 96 structural instances: reference 96/96 in each arm, budget-omission probe 0/96 neutral versus 96/96 reserve, and proxy 0/96 in each arm.
- A separate fresh eight-seed offline study collected and replayed 96 episodes from the clean published commit. Reference accepted 16/16 per arm; the probe accepted 0/16 neutral and 16/16 reserve; proxy accepted 0/16 per arm. These constructed controls validate the implementation, not model effect sizes.
- The ordinary 32-episode demo, 576 historical 2.0 episodes and the four earlier 2.1 live episodes replayed successfully. All 156 frozen historical files and the 72-trace legacy release passed their integrity checks.
- [CI at the preregistered core revision](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35335129750) passed on Windows/Linux and Python 3.11/3.13.

The reusable study workflow is implemented. Its empirical gate remains open; this pilot records why collecting a larger sample is not the next useful action.
