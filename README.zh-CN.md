# POMDP 智能体评测框架

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[English](README.md) · [路线](docs/ROADMAP.zh-CN.md) · [设计](docs/DESIGN.md) · [接入模型](docs/MODEL_ADAPTERS.md)

评估智能体能否在信息不完整、资源有限的情况下，交付**通过验收、有实际价值的成果**。
完整轨迹是评测单位；失败尝试、执行故障和交付成本都保留。

**当前主线是完整的开放式事故处置。** [结算事故环境](docs/SERVICE_INCIDENT.md)
运行真实 HTTP 请求、持久化订单、消息队列和账本。模型接手模糊故障，自主调查、
处置、获取反馈、恢复积压并核账交付。临时造成的重复扣款暴露会留在轨迹里。

这是构造的本地业务系统，不是声称来自生产的真实事故。强模型必须跑完整交互才能校准难度。
定位辅助的一次补丁测试已退出开发主线；2.8 的三个源码修复题和所有历史结果保留为参照。

```powershell
python -m pip install -e .
python studies/settlement-incident-v1/controls.py artifacts/incident-controls
python -m pomdp_bench validate artifacts/incident-controls
```

无需 Docker。模型只通过运维接口操作可信服务，不在本机执行模型生成的代码。
[逐步路线](docs/ROADMAP.zh-CN.md)与[完整交互规范](docs/SERVICE_INCIDENT.md)。

## 实现路径与架构

```text
事故目标与验收要求
  → 公开观察 → 模型动作 → 实际服务操作
  → HTTP／SQL 结果与变化后的业务状态 → 下一步决策
  → 调查／修复／恢复／验证 → 主动交付
  → 完整轨迹、业务结果与累计损害
```

所有任务复用一个采集器。源码、镜像、预算和尝试与证据绑定。
模型获得公开工具结果，不获得私有清单、上游答案或评分器。
任何修改都会使旧验证失效；失败留在分母中，缺少用量保持未知。

## 运行

Python 3.11+，评测器使用标准库；执行候选代码还需要支持 Linux 容器的 Docker。
PowerShell 示例：

```powershell
python -m pip install -e .
docker pull python:3.13-slim
$repairImage = docker image inspect python:3.13-slim --format '{{.Id}}'
python studies/repository-repair-v1/controls.py --image $repairImage --out artifacts/repair-controls
python -m pomdp_bench validate artifacts/repair-controls
```

[六项固定对照](studies/repository-repair-v1/README.md)检查正确修复、不改源码、
只通过报告样例、验证后改动、篡改测试与空进程成功退出。
上游补丁是产物验收对照，不是模型成绩。对照命令也会用新容器重新执行检查。

`validate` 核对已记录行为，不运行候选代码。
`recheck` 使用固定镜像重新执行并比对原记录。
模型任务沿用 `chat`／`responses` 配置和
[`prepare`／`resume` 流程](docs/REPOSITORY_REPAIR.md#run)。
凭据留在环境变量和请求头；完成或中断的尝试不会静默重跑替换。

没有 Docker 或模型账号也能运行合成回归对照：

```powershell
python -m pomdp_bench demo --out artifacts/demo --count 3
python -m pomdp_bench validate artifacts/demo
```

## 开发取舍与结果

按 **质疑 → 删除 → 简化和优化 → 加速 → 自动化** 的顺序工作。

- 主线是修复真实问题、保护相关行为并交付可审查补丁。
- 诊断、依赖发现和覆盖搜索保留为对照。
- 删除“扩大合成目录、完成历史压缩后才能做真实工作”的前置条件。
- 复用采集、模型接入和证据校验，不另造调度器、插件体系或智能总分。
- 难度来自跨文件诊断、兼容性约束和失败恢复；用强模型实测，
  随能力进步扩展，同时保留固定历史参照。

[逐步路线](docs/ROADMAP.zh-CN.md)给出交付物与删除条件。
分别报告通过验收的补丁、工具步骤、检查次数、修改文件数、耗时、用量和执行故障。
修复任务按源问题聚类，合成任务按种子聚类。
反复运行一个公开问题不会产生更多独立任务。未测量的人工介入时间不编造。

已发布研究保持原样，入口见[证据索引](README.md#preserved-evidence)。
最近的[深度试跑](studies/coverage-depth-v1/README.md)保留两条直接模式请求超时、
两条带工具成功；固定脚本可完成全部 24 个合格实例。
据此将覆盖任务保留为搜索和工具使用对照，把主线推进到实际代码交付。

## 验证与贡献

```powershell
python -m unittest discover -s tests -v
python tools/verify_study.py
python tools/verify_release.py
python tools/check_docs.py
```

[pomdp_bench/](pomdp_bench/) 是环境、模型接入、采集与重放；
[docs/](docs/) 是规范；[studies/](studies/) 保存证据。
`harness/`、`results/`、`reports/` 是冻结的历史材料。

[贡献](CONTRIBUTING.md) · [隔离](SECURITY.md) · [版本](CHANGELOG.md) · [引用](CITATION.cff)

项目代码与文档使用 [Apache-2.0](LICENSE)。
内置源码快照保留各自的[上游许可证](pomdp_bench/repair_data/README.md)。
项目独立维护，与模型供应商无隶属或背书关系。
