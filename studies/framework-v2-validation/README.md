# Framework 2.0 implementation validation

Collected on 2026-09-18 from clean source commit `0e405f4`. Full source hashes, runtime details, stratified results and sampling settings are in [summary.json](summary.json).

This is **scripted-control validation**, not a model leaderboard or external-validity study. No external model API calls were made. The separate HTTP adapter integration test uses a local deterministic fixture.

## Design

24 development seeds (100–123) × 2 families (`diagnosis`, `cascade`) × 3 profiles (`standard`, `wide`, `deep`) × 4 scripted policies = **576 episodes**, covering **144 generated cases**. The domain skin is `incident`, the condition is `open`, and each cell has one replicate. Cases sharing a seed belong to the same uncertainty cluster.

| Public-information policy | Accepted | Episodes |
|---|---:|---:|
| Reference diagnostic-tree planner | 144 | 144 |
| Random action policy | 4 | 144 |
| Overdiagnosis negative control | 0 | 144 |
| Cosmetic-success negative control | 0 | 144 |

All 576 episodes passed case regeneration, observation-by-observation replay, state-derived grading, and complete-matrix validation. These controls demonstrate that the generator admits successful public-information policies and that the grader separates the designed failure strategies on this development suite. They do not establish discrimination between frontier models, broad cognitive validity, or real-work predictive accuracy.

The test suite additionally contains 180 generated reference-policy checks across 30 other seeds and all family/profile combinations. It covers failed and stale verification, side-channel projection, mutation/rollback, free-action step exhaustion, tampered traces, missing episodes, malformed model actions, unknown token usage, arbitrary agent names, and a real localhost HTTP request/response loop.

Historical validation checks the frozen 156-file v1 archive and confirms that stronger current-state closure does not change the 72 published binary outcomes. The historical scorer's defects and metadata side channels remain documented rather than hidden.

## Reproduce

```bash
python -m pomdp_bench generate --seed 100 --count 24 --profiles standard wide deep --out artifacts/private/validation-suite.json
python -m pomdp_bench run --suite artifacts/private/validation-suite.json --agents examples/agents.json --out artifacts/validation-run
python -m pomdp_bench validate artifacts/validation-run
python -m unittest discover -s tests -v
```

The published JSON includes the complete aggregate output and source fingerprints. Full traces are generated locally by these commands; the private run directory is intentionally not bundled into the repository. Timing is machine-dependent. Structural and scripted-control results are deterministic under the recorded generator/policy versions.
