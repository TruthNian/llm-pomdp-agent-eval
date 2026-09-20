# POMDP 代理评测框架

[![CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/workflows/ci.yml)
[English](README.md) · [设计依据](docs/DESIGN.md) · [评测规范](docs/SPECIFICATION.md) · [接入模型](docs/MODEL_ADAPTERS.md)

评估代理在信息不完整的情况下，如何**获取证据、理解问题、选择行动、分配资源、从错误中恢复并完成验收**。

现实中的问题往往在执行过程中逐渐显露。每次行动都会同时改变已知信息、环境状态和后续选择。这里以完整交互轨迹为评测对象，用环境的真实终态判定任务是否完成。

**2.5 版加入结构难度阶梯与局部恢复**：智能体需要发现重叠操作，在有限执行额度内选择全局可行组合，并在变化后保留有效成果、恢复失效目标。四档规模最高包含 48 个目标、96 个备选操作。公开信息精确搜索与较强局部启发式已有明显差异；[真实强模型校准](studies/coverage-calibration-v1/README.md)单独报告。真实工作效度仍需验证；原先 72 条 GPT/GLM 实验保留为[历史研究](studies/2026-gpt56-glm53/README.md)。

**高难度、可持续提高且确有区分度，是项目的核心验收要求。** [难度维护规范](docs/DIFFICULTY.md)要求检验天花板与地板效应、保留固定版本参照，并随模型进步校准新档位。任务变长、名字叫“极难”，都不算难度证据。

开发按[分阶段路线与验收关卡](docs/ROADMAP.zh-CN.md)推进：可靠采集 → 单项机制实验 → 新任务结构 → 真实工作效度 → 度量后的加速。先质疑需求、删除不必要的内容，再简化和优化，最后自动化。长实验可用 [`prepare`、`status`、`resume`](docs/COLLECTION.md)；已经完成或中断的尝试不会被悄悄重跑替换。

单项干预实验使用 [`prepare-study`](docs/STUDIES.md)，[离线示例](examples/study-reserve.pilot.json)无需调用模型。主分析只比较同一模型在两种提示下的配对结果；超时保留在分母中，并单独报告其造成的解释范围。小样本全成功也不会被报告成确定的总体效果。

[预注册的 8 条真实模型试跑](studies/verification-reserve-pilot-v1/README.md)已完整发布，包含两条接入失败和本机运行时的能力边界遗漏。结果没有证明预算提醒有效；下一步先验证动作通道，再考虑扩大采集。

[第一轮直接 HTTP 验证](studies/direct-channel-validation-v1/README.md)保留了 4 条首请求失败。[2.4 独立后续验证](studies/direct-channel-validation-v2/README.md)中，两种模型各完成一条多阶段任务，另两条分别因流失败和超时终止。**整组接入验收仍未通过。** 4 条均完整重放；开发诊断单独报告，旧失败不被替换。

## 无需模型账号即可运行

新任务结构已有[版本化的依赖发现与恢复离线原型](docs/DISCOVERY_RECOVERY.md)。
[60 条完整对照轨迹](studies/discovery-recovery-v1/README.md)检验未知操作的获取、变化后的信息失效与重建，
并通过移除对应障碍，让相关失败策略恢复成功。它尚未加入正式评分家族，也不是模型成绩。
原型单独运行与重放：

```powershell
python -m pomdp_bench.discovery_controls --out artifacts/discovery-controls.json
python -m pomdp_bench.discovery_controls --validate artifacts/discovery-controls.json
```

Python 3.11+，运行时只使用标准库。在仓库根目录执行：

```powershell
python -m pomdp_bench demo --out artifacts/demo
python -m pomdp_bench validate artifacts/demo
```

同一批生成任务交给四种策略：

| 策略 | 输入 | 用途 |
|---|---|---|
| `reference` | 公开任务与观察 | 正对照：按可靠检测决策树收集信息，修复、验收、交付 |
| `random` | 公开动作目录 | 随机动作基线 |
| `overdiagnose` | 公开任务与观察 | 负对照：把全部诊断检查两遍后才行动 |
| `proxy` | 公开任务与观察 | 负对照：把仪表盘改成健康后交付 |

参考策略不读取隐藏答案。它在“可靠检测决策树”这个限定策略类内计算最坏情形成本最小的方案，并非全局最优 POMDP 求解器。评分器另行记录知道答案时的动作成本下界。

[已发布的实现验证](studies/framework-v2-validation/README.md)：144 个生成实例、576 条重放轨迹；参考策略 144/144，随机策略 4/144，两个负对照均为 0/144。这些是脚本策略验证结果，不是模型成绩。

输出包含 `summary.json` 和 `private/` 中的运行清单、轨迹。`validate` 会重新生成实例、重放动作、核对评分，并拒绝缺失或重复记录。输出目录存在时拒绝覆盖。评测期间应让代理无法读取私有文件。

也可用 `python -m pip install -e .` 安装 `pomdp-bench` 命令。

## 为未来模型生成新任务

新的规划／恢复阶梯复用现有采集器：

```powershell
python -m pomdp_bench generate-cover --fresh --count 12 --scales sanity challenge hard extreme --out artifacts/private/cover.json
python -m pomdp_bench prepare --suite artifacts/private/cover.json --agents examples/coverage-agents.json --out artifacts/cover
python -m pomdp_bench resume artifacts/cover
python -m pomdp_bench validate artifacts/cover
```

批量探查和执行按成员数量计费，减少无意义的调用往返。`--stable` 移除变化，`--slack N` 放宽执行额度，
必须作为预先声明的消融条件；不能在失败后替换原试验。档位名称只说明结构规模，是否难倒强模型需要实测。
原来的诊断任务继续按既有语义生成：

```powershell
python -m pomdp_bench generate --fresh --count 24 --families diagnosis cascade --profiles standard wide deep --out artifacts/private/suite.json
python -m pomdp_bench run --suite artifacts/private/suite.json --agents examples/agents.json --conditions open principles procedural --out artifacts/controls
python -m pomdp_bench validate artifacts/controls
```

`--fresh` 使用新生成的私有种子。开发时可用 `--seed 0` 重现任务，公开开发种子不应算作留出测试。

生成器改变候选假设、检测集合划分、成本、可靠性、目录顺序、真实故障和阶段结构。重复运行改变观察噪声，不算新的独立任务。`wide` 增加候选数量，`deep` 扩大多阶段深度；若用于泛化评测，应在调参前预先留出。

| 家族 | 信息如何出现 | 主要考验 |
|---|---|---|
| `diagnosis` | 从多个原因中诊断；便宜检测可能出错，可靠检测更贵 | 信息价值、何时停止、资源分配 |
| `cascade` | 修复前一阶段后才出现下一阶段的诊断目录 | 调整策略、丢弃失效假设、预留预算 |

错误修复会留下需要回滚的损害。健康覆盖只能改变表面状态。强验证必须通过，任何后续状态修改都会使验收失效。免费、无效和预算不足的动作同样占用步骤额度。

目前 `incident` 与 `data_pipeline` 是同一内核的两种语义外观，用于配对测试，不能代表两个独立现实领域。详见[测量边界](docs/DESIGN.md#measurement-boundaries)。

## 接入任意命名的模型

新运行器与统计支持任意模型名称、任意数量的比较组。`chat` 和 `responses` 适配器只发送公开任务、当前观察和已有动作，不启动智能体运行时或工具执行器，也不提供 shell、文件系统、种子、答案或评分器工具。Responses 接口可用[对应配置示例](examples/responses-agent.example.json)。

1. 复制[配置示例](examples/chat-agent.example.json)，填写模型标识及供应商支持的推理参数。
2. 设置本地环境变量：完整 HTTPS 端点 `BENCH_CHAT_ENDPOINT` 和凭据 `BENCH_API_KEY`。
3. 使用相同任务集运行各模型与提示条件：

```powershell
python -m pomdp_bench run --suite artifacts/private/suite.json --agents my-agents.json --conditions open principles procedural --replicates 3 --out artifacts/models
```

调用产生正常的供应商费用。凭据不写入配置或轨迹。推理档位须显式配置、如实报告；程序不会自行把不同供应商的档位视作相同计算量。详见[模型接入说明](docs/MODEL_ADAPTERS.md)。

## 如何理解结果

主指标是**通过验收的完成率**：全部阶段修复、损害清理、覆盖关闭、最新状态通过验证，并在预算内主动结束。

普通运行汇总展示各家族与配置的表现、每个成果承担的动作成本和 token、确定答案后的冗余检测、错误修复、表面指标操纵及预算损失；提供严格配对比较、提示敏感性与按种子聚类的 bootstrap 区间。失败仍计入分母，缺少用量时显示 `null`。

预注册实验以绑定计划的 `study_analysis` 为主分析，使用种子级 Hoeffding 同时区间，并单列接入中断造成的识别范围。此时通用汇总中的 bootstrap 字段只作描述性兼容输出。

不设置任意加权的“智能总分”。程序提示带来的提升只说明对本次干预的敏感性，解释为内在自主性需要额外证据；token 也不直接等于费用或 FLOPs。详见[指标定义](docs/SPECIFICATION.md#metrics-and-comparison)。

## 长期维护的原则

长期资产是可检验的规范、环境与证据：

1. 生成器、任务接口、状态转移、提示和评分规则均记录版本。
2. 真实状态与评分在代理观察边界之外。
3. 用只依赖公开信息的策略验证可解性。
4. 用负对照检查评分能识别表面成功和有缺陷的策略。
5. 同时检验新实例与新任务结构。
6. 冻结已发布研究；测试集退役后公开清单与轨迹。
7. 通过真实工作任务验证外部效度，再讨论部署表现。

已有交互式评测覆盖了其中许多问题。项目与 AgentBoard、τ-bench、OSWorld、InfoSeeker 的关系见[相关研究](docs/RELATED_WORK.md)，后续实验与验收门槛见[路线图](docs/ROADMAP.zh-CN.md)。

## 代码与历史数据

```text
pomdp_bench/  生成器、环境、策略、接入、运行器、重放、统计
examples/     离线策略与模型配置
docs/         设计、规范、效度、扩展与版本管理
tests/        状态转移、生成、泄露、重放、HTTP、数据完整性
studies/      历史索引及不可变文件哈希
harness/      v1 历史实现
results/      v1 轨迹与统计
reports/      v1 报告
```

历史文件保留原路径，已有链接继续可用。[效度说明与勘误](studies/2026-gpt56-glm53/ERRATA.md)单独记录，避免用新版定义重写旧结果。

```powershell
python -m unittest discover -s tests -v
python tools/verify_release.py
python tools/verify_study.py
```

[贡献指南](CONTRIBUTING.md) · [隔离边界](SECURITY.md) · [版本变化](CHANGELOG.md) · [引用信息](CITATION.cff)

代码、文档与已发布合成数据使用 Apache-2.0 许可证。项目独立维护，与供应商无隶属或背书关系。
