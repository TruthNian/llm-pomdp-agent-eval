# Verification reserve: preregistered feasibility pilot

**Status: plan frozen before live collection.** The [machine-readable plan](plan.json) is published before model calls. Results will be appended after the complete fixed matrix has been collected and validated; the plan will not be edited in response to outcomes.

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
