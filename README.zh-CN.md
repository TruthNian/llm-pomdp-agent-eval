# POMDP 智能体评测框架

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[English](README.md) · [路线](docs/ROADMAP.zh-CN.md) · [设计](docs/DESIGN.md) · [接入模型](docs/MODEL_ADAPTERS.md)

评估智能体能否在信息不完整、资源有限的情况下，交付**通过验收、有实际价值的成果**。
完整轨迹是评测单位；失败尝试、执行故障和交付成本都保留。

**当前主线是最少信息的事故接手。** [2.13 PostgreSQL 候选](docs/POSTGRES_TAKEOVER.md)
提供普通终端，运行真实数据库分叉与持续客户流量，在交付后独立验收业务。
没有全知 verify 或事故专用操作菜单。[强模型筛选记录](studies/incident-takeover-v1/README.md)单独报告实测结果。

此前的[结算事故环境](docs/SERVICE_INCIDENT.md)
运行真实 HTTP 请求、持久化订单、消息队列和账本。模型接手模糊故障，自主调查、
处置、获取反馈、恢复积压并核账交付。临时造成的重复扣款暴露会留在轨迹里。

这是构造的本地业务系统，不是声称来自生产的真实事故。强模型必须跑完整交互才能校准难度。
定位辅助的一次补丁测试已退出开发主线；2.8 的三个源码修复题和所有历史结果保留为参照。

```powershell
python -m pip install -e .
python -m pomdp_bench prepare-settlement-suite --out artifacts/external-suite.json
python -m pomdp_bench run --suite artifacts/external-suite.json --agents examples/settlement-agents.json --out artifacts/external-run
python -m pomdp_bench validate artifacts/external-run
```

无需 Docker。模型通过运维接口操作可信服务；候选 SQL 只在受限 SQLite 中读取复制的公开输入，本机不执行模型生成的 shell／Python。
[逐步路线](docs/ROADMAP.zh-CN.md)与[完整交互规范](docs/SERVICE_INCIDENT.md)。

[实测完整轨迹与证据](studies/settlement-incident-v1/README.md)：Sol 用 20 步完成交付；
GLM 的原始尝试在 13 步后被旧解析器终止，这不能视为认知难度证据。
两次结果、过程中产生的业务损害和独立重执行均已保留。
当前场景是完整工作流参照，尚未达到项目要求的前沿高难度。

单独固定配置的 [GLM 追加验证](studies/settlement-incident-v2/README.md)已用 26 步交付，
期间从两次非法动作响应中继续恢复，最终 33 笔已接收订单全部核平。
原失败仍然保留；两个接入层版本的结果不混成模型排名。

2.11 新增[跨组件对账修复](docs/RECONCILIATION_REPAIR.md)：在两类不同金融数据契约中实际修改 SQL、执行中间结果、部署并回填历史数据。[完整证据](studies/reconciliation-repair-v1/README.md)保留十三条对照及两次因传输故障中断的 Sol max 尝试。已生成的 SQL 经单独脚本探针检验通过，但两次在线尝试均未完成交付，不能据此宣称高难度。

单独冻结的[网络恢复补测](studies/reconciliation-repair-v2/README.md)中，Sol max 在两个契约都用 28 步完成交付，无非法动作或传输错误。两题归入回归参照，高难度仍未得到证明。[2.12 退款实测](studies/refund-recovery-v1/README.md)也已完成：Sol max 用 39/100 步交付，无非法动作或多退款。本次未达到高难度目标，停止继续扩小型 SQL 构造题作为前沿主线。

2.10 新增[外部结算场景](docs/EXTERNAL_SETTLEMENT.md)：外部状态与本地账本分离，退款资金有限，取消有截止时间，通知会延迟和乱序。本地冲账无法撤销外部付款。[完整实测证据](studies/external-settlement-v1/README.md)：Sol 26 步交付；GLM 路由在九步后第十次请求超时。七项机制对照符合预期。配置不变性检查未通过，异常原样披露；本轮只作集成证据，不作严格模型对比，也不证明前沿难度。

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

## 其他任务族

Python 3.11+，评测器使用标准库。源码修复任务还需要 Linux Docker 容器，
其[运行方法](docs/REPOSITORY_REPAIR.md#run)、[六项对照](studies/repository-repair-v1/README.md)
和[三题结果](studies/repository-portfolio-v1/README.md)继续保留。
`validate` 核对已记录行为；`recheck` 重新执行原动作并比对结果。
凭据留在环境变量和请求头；完成或中断的尝试不会静默重跑替换。

没有 Docker 或模型账号也能运行合成回归对照：

```powershell
python -m pomdp_bench demo --out artifacts/demo --count 3
python -m pomdp_bench validate artifacts/demo
```

## 开发取舍与结果

按 **质疑 → 删除 → 简化和优化 → 加速 → 自动化** 的顺序工作。

- 主线是完整调查、处置、恢复并交付有用的业务结果。
- 诊断、依赖发现和覆盖搜索保留为对照。
- 删除“扩大合成目录、完成历史压缩后才能做真实工作”的前置条件。
- 复用采集、模型接入和证据校验，不另造调度器、插件体系或智能总分。
- 难度来自证据判断、兼容性约束和失败恢复；用强模型实测，
  随能力进步扩展，同时保留固定历史参照。

[逐步路线](docs/ROADMAP.zh-CN.md)给出交付物与删除条件。
分别报告交付验收、过程中的业务损害、操作数、耗时、用量和执行故障。
服务任务按事故场景聚类，修复任务按源问题聚类，合成任务按种子聚类。
反复运行一个场景不会产生更多独立任务。未测量的人工介入时间不编造。

已发布研究保持原样，入口见[证据索引](README.md#preserved-evidence)。
最近的[深度试跑](studies/coverage-depth-v1/README.md)保留两条直接模式请求超时、
两条带工具成功；固定脚本可完成全部 24 个合格实例。
据此将覆盖任务保留为搜索和工具使用对照。

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
