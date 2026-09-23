# 用户指定的三个模型补测

状态：计划已冻结，结果尚未取得。用户要求暂停开发，仅测试 GLM-5.3、GPT-6 Sol 和 GPT-6 Luna。
不修改框架、场景、镜像、评分或既有实验记录。每个模型各一次完整尝试：max 推理、200 步、单次 600 秒、整轮 10800 秒、16 MB 响应上限。

| 请求路由 | 固定计划 | 接入与测量边界 |
|---|---|---|
| gpt-6-sol | [计划](gpt6-sol-plan.json) | 既有 responses_session，保留原生对话和加密推理状态 |
| gpt-6-luna | [计划](gpt6-luna-plan.json) | 既有 responses_session，保留原生对话和加密推理状态 |
| custom/z-ai/glm-5.3 | [计划](glm53-plan.json) | 既有 responses_tools，每步重传公开历史，不保留原生推理连续性 |

本机 GLM 代理把推理转换为明文 summary，不能直接满足现有连续接口的 encrypted_content 契约。
这里预先声明使用已有工具接口，不在采集中悄悄降级。此差异限制跨模型比较；只报告各自配置下的业务结果。
请求路由也不是底层权重认证。

三个隔离环境可在同一主机并行运行。运行中真实客户流量和共享主机负载不完全相同；不声称配对的同一实时工作量。
所有失败保留，接口错误和资源故障不解释为认知难度，不补提示、不换成功样本。

此前 GLM 曾在[结算场景](../settlement-incident-v2/README.md)用 26 步完成，也分别在
[外部结算](../external-settlement-v1/README.md)和[PostgreSQL 接手](../incident-takeover-v1/README.md)
遭遇超时与响应大小限制。最新[连续 Sol 筛选](../stream-recovery-continuous-v1/README.md)只有 GPT-5.6 Sol，
已因完成交付而停止扩测；本轮是用户另行指定的追加测试，原计划和结论不变。
