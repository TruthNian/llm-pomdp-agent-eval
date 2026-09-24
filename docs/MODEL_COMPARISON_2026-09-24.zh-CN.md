# 同一事故的跨模型与推理强度对比（2026-09-24）

本记录汇总已经结束的 `stream-recovery/1` 完整轨迹及另列的接入中断，**不改写任何冻结成绩**。各配置使用同一构造事故、种子 2718、相同镜像和交接后业务评分，每个配置只有一次实时运行。原有 GPT-5.6 Sol、GPT-6 Sol、GPT-6 Luna 三条 `max` 连续 Responses 轨迹的 suite 哈希、初始观察、公开契约、运行时、源码哈希完全一致，除模型名外的代理配置也一致。新增 GPT-6 Astra 使用同一事故与连续 Responses 接口，独立测试 `medium`、`xhigh`、`max`，但强度不同。GLM 两条轨迹共用一套 Codex 代理接口，与 Responses 接口不同。客户流量随真实时间发生，实际请求序列并不逐条相同；因此下表是**单次配置下观察到的行为**，不是模型总体成功率、普遍能力排名，或参数规模、后训练、推理强度的因果估计。

| 模型 / 推理强度 | 会话接口 | 已接受工作的验收 | 重启后订单错误 / 漏发 | 动作 / 200 | 运行期间写失败 / 尝试 | 总用时 |
|---|---|---|---:|---:|---:|---:|
| [GPT-5.6 Sol `max`](../studies/stream-recovery-continuous-v1/README.md) | 连续 Responses | 通过 | 0 / 0 | 31 | 128 / 206（62.1%） | 22.3 分钟 |
| [GPT-6 Sol `max`](../studies/stream-recovery-requested-models-v1/README.md#已完成gpt-6-sol) | 连续 Responses | 通过 | 0 / 0 | 27 | 34 / 88（38.6%） | 10.5 分钟 |
| [GPT-6 Luna `max`](../studies/stream-recovery-requested-models-v1/README.md#已完成gpt-6-luna) | 连续 Responses | 失败 | 12 / 9 | 28 | 0 / 210 | 24.9 分钟 |
| [GPT-6 Astra `xhigh`](../studies/stream-recovery-astra-efforts-v1/README.md) | 连续 Responses | 通过 | 0 / 0 | 16 | 22 / 76（28.9%） | 9.7 分钟 |
| [GPT-6 Astra `max`](../studies/stream-recovery-astra-efforts-v1/README.md) | 连续 Responses | 通过 | 0 / 0 | 15 | 44 / 108（40.7%） | 13.5 分钟 |
| [GLM-5.3 `high`](../studies/stream-recovery-codex-native-glm-v1/README.md) | Codex 代理运行时 | 失败 | 12 / 9 | 37 | 0 / 98 | 12.8 分钟 |
| [GLM-5.3 `max`](../studies/stream-recovery-codex-native-glm-max-v1/README.md) | Codex 代理运行时 | 通过 | 0 / 0 | 44 | 32 / 192（16.7%） | 21.0 分钟 |

动作数含最终 `finish`；总用时含环境准备与交接后独立验收，不能当作纯推理延迟。写失败分母是该轮持续客户流量实际发出的指令数，而非相同的固定请求集；百分比只描述本轮服务可用性。最终订单数也随各轮时长不同，不用于能力排序。评分器只要求**获得成功收据**的指令最终正确，另外报告拒绝的实时请求。表中“通过”的轨迹均有客户写失败；零错误的业务状态不能写成零中断交付。

## 哪些差异比较有意义

最清楚的行为分界是**恢复证据边界**。GPT-5.6 Sol 连续会话、GPT-6 Sol、GPT-6 Astra `xhigh/max` 和 GLM `max` 均发现普通物理备份与 WAL，恢复并合并旧分支历史，最后通过客户侧验收。GPT-6 Luna 和 GLM `high` 修复了连接器、事件或发货账本，也看到当前系统局部一致，却没有补齐 Kafka 中不存在的旧分支指令，均留下 12 个订单错误和 9 笔漏发。[匹配的实物反事实](../studies/stream-recovery-counterfactual-v1/README.md)证明，在早期 Sol 的固定动作后仅补齐历史数据即可消除此 12/9 缺口；它支持事故机制，**不能**代替另外两条模型轨迹各自的配对因果实验。

**同接口、同强度的四个 GPT `max` 配置**有相同的冻结任务与程序条件：GPT-5.6 Sol、GPT-6 Sol 和 GPT-6 Astra 都完成旧历史恢复，GPT-6 Luna 未完成。尤其在 GPT-6 内部，Sol 与 Astra `max` 本次交付、Luna `max` 本次失败，这是实在的轨迹质量差异；它不能单凭各一次运行升级为总体成功率排序。Luna 报告的推理 token 约 45,497，GPT-6 Sol 约 10,563，Astra `max` 约 5,232；更多被报告的推理 token 没有保证更好的结果，不能反过来当作推理质量指标。

**同一 GLM 接入的 `high` 与 `max`** 观察到另一种差异：`high` 用 37 步交接并遗漏旧历史；`max` 用 44 步做备份/WAL 恢复、修复多次失败命令，最终通过已接受工作验收。两轮报告的推理 token 分别约 10,670 和 30,082，但 `max` 还多用了约 8.2 分钟，并造成 32 次客户写失败；`high` 的写失败为 0。两次是不同时间、不同持续客户负载下的一次性运行，不能把成功差异或服务中断**归因**于强度标签。这里没有 GLM `low`，也没有 GPT-6 Sol/Luna `high` 的同场景结果。

**GPT-6 Astra `xhigh` 与 `max`** 分别用 16、15 步恢复备份/WAL 中的旧分支历史、合并业务状态并完成交接；重启后均为 0 个订单错误、0 笔漏发。`max` 这次少用 1 步，却比 `xhigh` 多用约 3.8 分钟，运行期间客户写入失败为 44/108 而非 22/76。因此按本次现实交付的时长和可用性看，不能简单说 `max` 优于 `xhigh`；两轮客户请求不是逐条配对，不能把差异归因于强度。Astra `medium` 在 7 个动作后，第 8 次模型请求返回 HTTP 502，未完成交接；其未处理业务状态和写入失败只说明中断影响，**不构成 medium 推理能力失败**。[三档冻结计划与完整记录](../studies/stream-recovery-astra-efforts-v1/README.md)保留这一结果。

**GPT-5.6 Sol 与 GPT-6 Sol 的 `max` 连续会话**确实是同一声明条件下的直接对照，而不只是“题目相似”。两者均通过；在各自这一次运行中，GPT-6 Sol 用 27 而非 31 步、10.5 而非 22.3 分钟，运行期间写失败为 34/88 而非 128/206。故对**这一次固定事故的已观察效率与可用性**，GPT-6 Sol 优于 GPT-5.6 Sol；没有必要中和掉这个事实。限制是实时流量没有逐条配对、每个模型只有一轮，不能据此给出总体胜率或确定模型世代带来的因果提升。若按现实交付同时看正确性与客户可用性，也不能只按现有 `success` 布尔值排名；跨 GLM 与 GPT 时尤其不能把各运行时报告的 token 直接换算成同质计算量或价格。

## 不能放进能力排名的记录

[GPT-5.6 Sol 的早期无状态 `max` 尝试](../studies/stream-recovery-v1/README.md)以 29 步交接，留下相同的 12/9 缺口；它每步重传公开历史，没有连续原生推理状态。后来的连续会话成功不能由这两次非配对轨迹单独证明是接口所致，但早期失败也不能作为该模型连续代理能力的上限。[最初指定三模型补测](../studies/stream-recovery-requested-models-v1/README.md)中，GLM 原生工具首次请求零步接入失败，文本补测第十次请求超时；这些是协议/超时结果，不能列为模型做完事故后的认知失败，也没有被后续 GLM `high/max` 成绩覆盖。

[Boyue 同一 API 下七次前沿模型尝试](../studies/stream-recovery-boyue-frontier-results-v1/README.md)分别覆盖 Kimi K3、DeepSeek V4 Pro、MiniMax M3 和 Qwen3.8 Max 的普通 Chat 工具及 SSE 接入。七次均在交接前因传输或接口错误中止，其中 MiniMax 普通 Chat 执行到 40 步，其余为 0 步。它们是**接入可靠性的测量**，不能放进事故解决能力排名；冻结计划、逐轮错误与可离线重放记录均已保留。

## 对下一轮评测的判断

本事故已有五种配置完成，**不再足以证明前沿高难度**。继续在同一个固定事故上堆单次高强度调用，会强化熟悉题目的证据，却难以估计模型间稳定能力差异。若要回答“推理强度是否真正提高现实交付”，先统一代理接口与公开工具、版本化客户可用性和失败请求重试指标，再冻结多个独立、可解且更难的事故任务，对每个模型与强度使用同一任务集合和预算，保留全部失败与资源成本。做不到共同接入时，应明确报告“配置整体”差异，不能称为纯模型差异。当前证据最坚实的结论仍是**发现并恢复不可见的已接受历史**决定了这一次事故的业务正确性；服务中断成本还未进入通过门槛。

复核入口：[三模型补测](../studies/stream-recovery-requested-models-v1/README.md)、[连续 Sol](../studies/stream-recovery-continuous-v1/README.md)、[GLM `high`](../studies/stream-recovery-codex-native-glm-v1/README.md)、[GLM `max`](../studies/stream-recovery-codex-native-glm-max-v1/README.md)、[Astra 三档](../studies/stream-recovery-astra-efforts-v1/README.md)、[Boyue 前沿尝试](../studies/stream-recovery-boyue-frontier-results-v1/README.md)。各研究保留其冻结计划、轨迹或审计证据与离线复核命令。
