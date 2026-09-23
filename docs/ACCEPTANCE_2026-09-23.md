# 阶段验收：2026-09-23

**当前成果可以验收为可执行、可审计的事故恢复评测闭环，不能验收为已经达成高难度 POMDP benchmark。**
按用户要求，后续开发暂停，等待验收。代码、完整成功与失败轨迹、对照实验均保留；不启动新场景或追加模型测试。

## 建议验收顺序

1. 阅读本页，确认阶段范围与未完成目标。
2. 打开[最新完整轨迹](../studies/stream-recovery-continuous-v1/trajectories.html)，检查模型实际收到的信息、每一步命令、输出、失败和最终交接。
3. 阅读[结果与测量边界](../studies/stream-recovery-continuous-v1/README.md)，运行下方离线复核命令。
4. 对照[旧尝试](../studies/stream-recovery-v1/README.md)与[匹配的实物实验](../studies/stream-recovery-counterfactual-v1/README.md)，确认失败没有被新结果覆盖。

## 已交付的可用能力

- 本机 WSL 与 Docker Engine 已运行，发行版与容器数据位于 E 盘；无需 Docker Desktop。真实实验已使用该环境。
- PostgreSQL 分叉、实际 `pg_rewind`、普通物理备份/WAL、Debezium、Kafka 与独立承运商账本共同执行事故。外部已发生发货不能通过修改应用数据库撤销。
- 模型从少量事故症状和通用终端接手，自行发现系统、工具、证据和风险。客户流量持续执行；模型交接后才进行独立业务验收和实际重启。
- `responses_session` 保留原生助手/工具对话、调用标识和加密推理连续性。加密内容只留在运行内存；公开证据保存投影与哈希。
- 同一采集框架保存源代码、镜像、预算、所有动作、业务结果和交付成本；公开复核不依赖再次调用模型。

环境与机制详见[场景说明](STREAM_RECOVERY.md)，接入约定见[模型适配器](MODEL_ADAPTERS.md)。
这是有公开事故来源参考的构造业务系统，不声称复现生产事故，也没有证明对生产能力的预测效度。

## 本阶段结果

| 实验 | 实际执行 | 结果与可支持的判断 |
|---|---|---|
| 旧无状态 Sol max | 29/200 步，自主交接 | 遗漏 12 个订单、9 笔发货；是真实业务失败，但接入未保留原生推理连续性 |
| 匹配实物对照 | 完整重执行旧模型的 28 条终端命令 | 保留原缺口；随后仅补回普通备份/WAL 历史，保持修好的流水线不变，即消除缺口；这不是新增模型尝试 |
| 原生连续会话 Sol max | 31/200 步，自主交接 | 重启前 105 个订单、89 笔应发货；重启后 111 个订单、93 笔应发货，均正确，无漏发、重复、错误或意外发货 |

最新尝试没有适配器、观察器或请求重试验收错误。维护期间 **128 次客户写请求失败**；四次终端调用返回非零，其他失败子命令也保留。
记录用时约 22 分 19 秒，包含环境准备与最终验收。31 次请求全部报告用量：累计输入 6,210,060 tokens、输出 30,625 tokens，其中推理 14,132 tokens。
累计输入包含重复上下文，不能当成独立信息量。

模型自行找到备份/WAL，恢复旧时间线，合并历史并保留原发货幂等标识，重建 CDC 后核对业务，再交接。
原生连续会话完整通过，按预登记规则淘汰此候选的高难度证据资格。本轮未运行 GLM；两次非配对模型尝试也不能证明连续会话适配器的因果效应。

## 复核与保存范围

最新实测的冻结源码为 `0b60e5d413bd449b53689db3b55dc29f5ffd0179`，镜像为
`sha256:9ae11d63ae5f3525160b23746fca3f080c976dd9e90956a4f16b12361c33862d`。
[执行清单](../studies/stream-recovery-continuous-v1/execution.json)绑定计划、结果、轨迹、诊断和复核脚本的哈希；
[机器可读证据](../studies/stream-recovery-continuous-v1/model-evidence.json)可独立重新计算记录中的业务验收结果。

在仓库根目录执行，均不调用模型、不启动 Docker：

```powershell
python studies/stream-recovery-continuous-v1/verify.py
python studies/stream-recovery-counterfactual-v1/verify.py
python studies/stream-recovery-v1/verify.py
python tools/verify_study.py
python tools/verify_release.py
python tools/check_docs.py
```

冻结功能代码的完整单元测试为 **233 项通过**。阶段收尾只增加结果与文档，不改模型、环境或评分代码。
收尾复核已通过上述三组实验验证、156 个历史文件校验、发布校验和 53 份 Markdown 的链接检查；另行执行的离线 demo 共 24 条轨迹，全部通过 `validate`。
公开复核覆盖已记录业务结果、文件绑定和每次请求的公开投影；不声称重建只保存在内存里的加密请求字节。
离线复核不等于重新执行事故；重新运行的实时流量可能不同。

本机原始运行目录保留在主仓库的 `artifacts/continuous-agent/artifacts/stream-continuous-sol-v1`。
旧实测与匹配对照仍在主仓库的 `artifacts/stream-sol-v1`、`artifacts/stream-counterfactual-original-v1`、
`artifacts/stream-counterfactual-restore-v1`。这些本地记录不等同于公开证据，私有配置和凭据不进入 Git。

## 尚未完成，不能提前验收

- **高难度和长期区分能力。** 当前场景已被连续会话强模型完成；不靠组件数量、数据量或旧传输失败宣称难度。
- **更广的业务覆盖。** 当前验收覆盖所有已接受订单的最终状态及应发货效果，但只由评估器抽取一个初始请求做相同/冲突重试，不穷举全部历史请求或下一次故障切换。
- **下一候选。** 尚未选定或实现。恢复开发后，应先定位当前简化业务省略的实际恢复依赖，再决定是否采用更完整的业务系统；不把这个方向写成已经完成的成果。

本次验收决定保留哪些基础能力、哪些需要返工；它不自动确认整体高难度目标完成。后续推进以用户验收意见为准。
