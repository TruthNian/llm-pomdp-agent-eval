# POMDP 智能体评测

[English](README.md) · [开发路线](docs/ROADMAP.zh-CN.md) · [设计](docs/DESIGN.md) · [模型接入](docs/MODEL_ADAPTERS.md)

检验模型能否独立接手陌生事故，自行调查、判断、处置和纠错，保全业务记录并完成客户工作。一次测试包含完整交互；模型使用正常工具，面对稀疏交接、运行噪声和实际操作后果，业务结果由独立验收检查。

**当前主线：一个事故、一个模型配置、一份结果。** 2.17 新增 `stream-recovery/2`，复用现有 PostgreSQL/Kafka 隔离环境与采集器。固定客户需求按原请求身份正常重试，验收覆盖全部需求，包括始终没有取得成功收据的工作；正确订单与发货还须通过真实重启检查。

```bash
python -m pip install -e .
python -m pomdp_bench benchmark --agent examples/benchmark-agent.example.json --runtime-config runtime.json --out artifacts/incident-test-001
python -m pomdp_bench validate artifacts/incident-test-001
```

在示例中填写模型 ID 和已有接入的环境变量名称；凭据从环境读取。`runtime.json` 使用 [stream 运行配置](docs/STREAM_RECOVERY.md#run-locally)，可复用已有 stream 镜像。[新版业务契约](docs/STREAM_RECOVERY.md#customer-delivery-version-2)说明客户策略与版本迁移。

输出 `result.md`、`result.json`、完整轨迹和独立审计。先判断业务是否交付及实际错误，再看分项 token、耗时和可核对费用。后台写请求失败次数仅作诊断，动作仅作内部预算；漏报与未知费用如实标明。接入中断与完成后业务失败分开记录，失败尝试不会被静默重试或覆盖。

这是构造的事故环境。高难度由完整模型行为检验，强模型通过的结果仍然保留；新版验收本身不证明前沿难度或广泛现实预测能力。

[最新完整验收](studies/stream-delivery-completion-v1/README.md)：GPT-6 Astra `max` 主动交接，12/12 客户需求、84 个订单及 60 笔发货通过重启后的独立检查。全部 17 次请求报告合计 656,034 token，费用未知。此前三次接入中断及真实操作对照分别保留。2.17.3 使用有限传输恢复、非动作元数据兼容与完整工具调用检查；本次成功不证明前沿高难度，也不改写此前成绩。

[既有模型对比](docs/MODEL_COMPARISON_2026-09-24.zh-CN.md)与全部版本化证据保留。以下历史任务用于回归与研究，不是默认单次测试的前置流程。

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
旧版显式验证任务在修改后使旧验证失效；事故接手则在交付后独立验收业务结果。
失败留在分母中，缺少用量保持未知。

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
