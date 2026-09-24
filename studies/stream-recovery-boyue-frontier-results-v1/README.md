# Boyue 前沿模型接入试验：七次完整保留的尝试

这些尝试使用本机已配置的 **GLM-5.3 同一个 Boyue API 和密钥**，请求不同的模型 ID。事故仍是 `stream-recovery/1`，同一个 suite、200 动作与 10800 秒整轮上限；每次尝试在自己的隔离环境中运行。非流式三模型计划、SSE 三模型计划、Qwen SSE `medium` 计划均在正式调用前冻结。`trace.json.gz` 保留动作、工具反馈、接入审计及独立业务评分；私有生成 suite、原始供应商响应和密钥没有入库。[复核脚本](evidence.py)可从公开生成器重建 case，复算七条记录的业务评分。

| 冻结计划 | 模型 ID | 动作 | 结束原因 | 最后请求的接入证据 |
|---|---|---:|---|---|
| [普通 Chat 工具](../stream-recovery-boyue-frontier-v1/plan.json) | `kimi-k3` | 0 | `adapter_error` | 首次请求连接中断，约 95.6 秒 |
| 同上 | `deepseek-v4-pro` | 0 | `adapter_error` | 首次请求连接中断，约 96.1 秒 |
| 同上 | `MiniMax-M3` | 40 | `adapter_error` | 第 41 次请求连接中断，约 29.6 秒 |
| [SSE 工具](../stream-recovery-boyue-frontier-sse-v1/plan.json) | `kimi-k3` | 0 | `adapter_error` | 首次请求在约 122.1 秒后断开，收到 0 个 SSE 事件 |
| 同上 | `deepseek-v4-pro` | 0 | `adapter_error` | 首次请求在约 119.2 秒后断开，收到 0 个 SSE 事件 |
| 同上 | `MiniMax-M3` | 0 | `adapter_error` | 首次响应有 6 个 SSE 事件，但不满足单次工具调用的冻结接口契约 |
| [SSE 工具，明确 `medium`](../stream-recovery-boyue-qwen38max-sse-v1/plan.json) | `qwen3.8-max` | 0 | `adapter_error` | 首次请求在约 128.2 秒后断开，收到 0 个 SSE 事件 |

**七次没有一次完成模型交接，因此都不是事故解决能力的有效判负。** 零动作轮次的订单错误只是无人修复的环境状态。MiniMax 普通 Chat 轮次虽然执行了 40 个动作，最后仍因接入中断没有完成验收；这段行为可供检查，却不能当成模型最终解题成绩。SSE MiniMax 收到完整响应但接口拒绝其调用形状：保留其哈希与结构错误，不推测未留存的供应商正文具体内容。路由返回的模型名只能证明接口标签，不能独立认证底层权重。

非流式首个请求的断连促使我们单独冻结 SSE 方案；SSE 没有解决 Kimi、DeepSeek 和 Qwen 的首事件前断连。此前小型多轮探针能通过，但正式事故的首次调用与其负载和时点不同，不能用探针成功替代正式结果。后续若改变路由、参数或处理多个工具调用，必须另开计划并保留这七次失败；不得把修复后结果覆盖到这些轮次。

```powershell
python studies/stream-recovery-boyue-frontier-results-v1/evidence.py verify
```

复核无需模型或 Docker 调用；它检查公开记录与冻结计划、源码哈希、完整留存数，并重放已有工具反馈与业务评分。`receipt.json` 另记录本机原始私有 checkpoint 的 SHA-256，便于现场对照；Git 仓库只发布去掉生成 case 的记录。
