# Boyue 前沿模型后续三次独立事故测试

在[先前三模型普通 Chat、SSE 与 Qwen 的七次记录](../stream-recovery-boyue-frontier-results-v1/README.md)之外，本轮继续使用**同一个 GLM-5.3 所配置的 Boyue API**。三条计划分别在首次正式调用前冻结，使用同一个 `stream-recovery/1` case、镜像、公开事故交接、200 动作和 10800 秒整轮上限；各模型拥有独立的隔离环境。失败不重试、不换样本，原先七条记录也未被覆盖。

| 模型与接口 | 动作 | 正式终止 | 重启后订单错误 / 漏发 / 意外发货 | 客户写入失败 | 总用时 |
|---|---:|---|---:|---:|---:|
| [MiMo V2.5 Pro，SSE，单工具调用](../stream-recovery-boyue-mimo25pro-sse-v1/plan.json) | 14 | 第 15 次请求 `incomplete_sse`，未交接 | 26 / 57 / 0（中断状态） | 0 / 42 | 7.8 分钟 |
| [Doubao Seed 2.1 Pro，普通 Chat](../stream-recovery-boyue-doubao21pro-chat-v1/plan.json) | 62 | 自主 `finish`，业务验收失败 | **26 / 140 / 2** | **72 / 280（25.7%）** | 32.1 分钟 |
| [MiniMax M3，SSE，单工具调用](../stream-recovery-boyue-minimaxm3-sse-serial-v1/plan.json) | 25 | 第 26 次请求 `incomplete_sse`，未交接 | 26 / 23 / 0（中断状态） | 0 / 44 | 8.1 分钟 |

**Doubao 是本轮唯一完成交接的模型，因此它的业务失败可以如实评价。** 它进行了 62 次有效工具动作，尝试修复 carrier、CDC 和消费位置，但完整轨迹中没有执行物理备份/WAL 恢复旧分支；交接后的独立客户侧验收仍发现上述错误。72 次失败写入是实际客户可用性损失，不能被最终订单状态掩盖。该配置报告 3,592,079 输入、23,592 输出 tokens，其中推理 9,653；输入累计包含不断增长的历史，不能与其他接口的 token 直接换算能力或成本。单次失败证明这一次配置未交付，不是总体成功率估计。

MiMo 的初始未评分探针在默认设置下返回两个合法 `exec` 调用；现有单动作环境适配器无法处理这样的响应。普通 Chat 参数 `parallel_tool_calls=false` 在同一个公开初始输入下返回一个合法调用，因此本轮在[新计划](../stream-recovery-boyue-mimo25pro-sse-v1/plan.json)中预先固定该选项；MiniMax 也单独固定同一选项。这不是事故提示，但与先前默认选项的实验条件不同。MiMo 和 MiniMax 均执行了真实动作，随后得到 `incomplete_sse`。现有审计只足以确认 SSE 完整结束条件未满足，**不能进一步断言是供应商连接截断，还是适配器对终止帧的要求过严**；更不能把未完成交接后的业务缺口归为模型认知失败。

[压缩机器轨迹](trace.json.gz)保存全部动作、工具反馈、结构化请求审计和业务评分，去掉私有生成 case，不含密钥或原始供应商响应。[收据](receipt.json)保存三份原始私有 checkpoint 的 SHA-256 供现场对照，并绑定公开轨迹哈希。离线复核不调用模型或启动 Docker：

```powershell
python studies/stream-recovery-boyue-frontier-recovery-v1/evidence.py verify
```

本轮测到的是这些 **Boyue 路由 + 接口 + 模型 ID** 在同一事故上的实际交付和接入状况；接口返回的模型名无法独立认证上游权重。要比较模型能力，必须先取得更多可完整交接的同任务轨迹，并把客户写入失败作为结果的一部分。
