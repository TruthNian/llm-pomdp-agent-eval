# Related work and the project's contribution

Interactive evaluation, partial observability, and state-based success are established research directions. This project should be assessed against those directions, not against the claim that all other benchmarks are static questions.

| Primary source | Established contribution | Relationship to this project |
|---|---|---|
| [AgentBoard](https://arxiv.org/abs/2401.13178), Ma et al. | Multi-turn agent evaluation with partially observable environments and fine-grained progress analysis | Supports inspecting trajectories and intermediate progress. This project adds a small generated kernel with controlled costs and exact reference policies. |
| [τ-bench](https://arxiv.org/abs/2406.12045), Yao et al. | Tool-agent-user interactions, policy following, database-state evaluation and repeated-run reliability | Demonstrates that real-world interaction and terminal-state evaluation are not new claims. This project's current simulator lacks τ-bench's user negotiation. |
| [OSWorld](https://arxiv.org/abs/2404.07972), Xie et al. | Open-ended tasks in real computer environments with execution-based evaluation | Supplies realism that the present abstract kernel does not. A future transfer study should compare controlled policy metrics with practical environment outcomes. |
| [Information Seeking for Robust Decision Making under Partial Observability](https://arxiv.org/abs/2510.01531) | InfoSeeker integrates planning with information seeking and evaluates incomplete observations and uncertain dynamics | Direct overlap with active information acquisition. The present generator exposes known test likelihoods and does not yet evaluate learning unknown dynamics. |

The maintained artifact here is a compact, inspectable experimental system combining:

- structural generation and declared stress profiles;
- an observation-limited solvability reference;
- open/principles/procedural policy interventions;
- reliable-test certainty and remaining-action feasibility diagnostics;
- revision-sensitive acceptance and adversarial negative controls;
- versioned manifests, complete-matrix validation and replay.

These are implementation and experimental-design commitments. They do not establish that the benchmark measures general intelligence or predicts real work better than the cited systems. The next scientific contribution must be evidence: held-out structures, component ablations, and prospective external-task validation. Novelty should be claimed at the level the evidence supports.

Primary sources were checked on 2026-09-18. Descriptions above are scoped to their published abstracts; no unverified performance comparison is made.
