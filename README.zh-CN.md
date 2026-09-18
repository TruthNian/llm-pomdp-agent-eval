# LLM POMDP 代理评测

这是一套开源、可复现的部分可观测代理评测方法，用来检验大模型能否把正确诊断稳定转化为安全的端到端行动。

仓库完整发布：隐藏状态模拟器、三种提示条件、Codex 运行器、评分逻辑、统计程序、72 条主实验轨迹、衍生数据和最终报告。项目采用 [Apache-2.0 许可证](LICENSE)。

[English README](README.md) · [完整方法](docs/METHODOLOGY.md) · [适配其他模型](docs/ADAPTING.md) · [数据说明](docs/DATA_CARD.md) · [中文完整报告](reports/gpt56_glm53_pomdp_final_report.html)

## 评测要解决的问题

静态 benchmark 通常检验模型能否得到正确答案。真实代理还必须管理信息价值和未来行动空间：

- 隐藏根因不可直接读取；
- 可观察信息包含可信干扰项；
- 日志、指标、探针、修复和验证都会消耗风险预算；
- 修复加深度验证必须预留 8 点预算；
- 健康覆盖、静默告警和放宽超时可以制造表面成功；
- 最终成功由隐藏状态程序化计算，模型的交接文字不能改变评分。

因此，这套环境能区分局部解题能力与自主停止、预算纪律、计划—执行一致性、闭环能力和抗捷径能力。

## 主实验设计

| 因素 | 水平 |
|---|---|
| 模型 | GPT-5.6 Sol、GLM-5.3 |
| 提示 | 开放目标、原则性提示、程序性控制 |
| 隐藏根因 | 数据库连接泄漏、缓存污染、时钟偏移、队列消费者卡死 |
| 重复 | 每个单元 3 次 |
| 总轨迹 | **72** |

两个模型使用相同 Codex CLI、工具边界、模拟器、隐藏状态和 `max` 推理强度。插件、浏览器、Computer Use、多代理、personality 和 hooks 均关闭。

## 核心结果

| 提示条件 | GPT 真成功 | GLM 真成功 |
|---|---:|---:|
| 开放目标 | 12/12 | 3/12 |
| 原则性提示 | 12/12 | 4/12 |
| 程序性控制 | 12/12 | 12/12 |

GLM 在 24 条非程序性轨迹中全部在变更前取得直接根因证据，却有 12 条因继续低价值诊断而使正确修复被预算阻断，最终只有 7 条达到安全终态。程序性提示把预算预留、证据阈值和停止规则外部化后，GLM 达到 12/12。

这说明 benchmark 接近可以与开放式代理能力明显分化同时成立。完整论证、token 效率、轨迹案例和训练机制分析见[中文报告](reports/gpt56_glm53_pomdp_final_report.html)。

## 从已有轨迹复算

只使用 Python 标准库：

```powershell
python harness/analyze_results.py
python tools/verify_release.py
```

## 重新运行 72 条实验

以下命令会调用远程模型并消耗大量 token：

```powershell
python harness/run_incident_eval.py --conditions open,explicit,procedural --models gpt,glm --replicates 3 --replicate-start 1 --workers 4 --timeout 900
python harness/analyze_results.py
```

原实验使用 `codex-cli 0.151.0-alpha.7.2`。运行新实验时请记录实际 CLI 版本、模型标识、日期和供应商配置。

适配其他模型时使用 `--model-spec KEY=MODEL_ID`；统计程序当前把 `gpt` 与 `glm` 作为两组配对实验键，具体方法见 [docs/ADAPTING.md](docs/ADAPTING.md)。

## 数据安全

仓库没有发布原始 Codex JSONL 事件流，因为模型运行期间可能在其中看到临时客户端配置。公开的 trace 保存了所有环境行动、观察、隐藏评分和聚合 usage，足以复核报告结论，同时避免分发运行期 bearer credential。

## 开源声明

本仓库的代码、文档、轨迹和报告采用 [Apache License 2.0](LICENSE) 开源。模型与产品名称归各自权利人所有；本项目是独立评测，与 OpenAI、智谱或 Z.ai 无隶属及背书关系。
