# Search strength and candidate difficulty structures

The released top scale is easy for the current specialized exact solver. Its
24 searches (12 public seeds, initial and recovery phases) visit at most **36
memoized states** each. The [completed public model pilot](../coverage-calibration-v2/README.md)
also records Sol solving the top scale on seed zero. Neither local-heuristic
failure nor the name `extreme` establishes lasting frontier headroom.

## Released anchors

| Scale | Calls | Solutions found | Minimum / median / maximum states |
|---|---:|---:|---|
| sanity | 24 | 24 | 3 / 3.5 / 6 |
| challenge | 24 | 24 | 6 / 8 / 20 |
| hard | 24 | 24 | 8 / 11.5 / 28 |
| extreme | 24 | 24 | 8 / 10.5 / 36 |

Each search uses the catalogue exposed by an actual public `probe`. The reference
builds and verifies its plan, then responds to the announced change. All 48
released episodes pass their final acceptance predicate. These are specialized
algorithm measurements, not generic agent scores or intrinsic complexity bounds.

## Exploratory initial-cover screening

Larger per-operation coverage can keep the required combination short even as
the catalogue grows. The released hard and extreme scales both need only eight
initial builds. This exploration varies required combination depth and overlapping
alternatives rather than only adding goal names.

| Goals | Width | Alternatives | Required builds | Found / 12 | Exceeded 5,000 states / 12 |
|---|---:|---:|---:|---:|---:|
| 36 | 3 | 72 | 12 | 12 | 0 |
| 48 | 3 | 96 | 16 | 12 | 0 |
| 60 | 3 | 120 | 20 | 12 | 0 |
| 48 | 4 | 144 | 12 | 12 | 0 |
| 72 | 4 | 216 | 18 | 8 | 4 |
| 96 | 4 | 288 | 24 | 0 | 12 |
| 96 | 4 | 384 | 24 | 0 | 12 |

All use public seeds 0–11, a separate experimental random stream, tight work
limits and **initial cover only**. Every generated instance contains a feasible
partition. Exceeding the search limit means unknown within this effort, never
infeasible. A limit of 5,000 states is this screening budget, not the released
reference's one-million-state limit. Completed-only search medians cannot rank
the full distribution when other calls are censored.

The shapes were selected after exploratory development; this is **not**
preregistered or held-out evidence. A preliminary screen used seeds 0–2 for the
first four shapes and 0–1 for the last three. The full report retains all 84
candidate calls, including those preliminary seeds and all exhausted searches.
No failed seed is replaced. No model requests, solver-assisted model results,
recovery claims or new released scales are included.

[Evidence](evidence.json) contains all 180 search calls, case/catalogue/plan hashes,
source fingerprints, search limits, censored outcomes and elapsed times.
[The executable script](screen.py) temporarily substitutes experimental dimensions
only in its own process. It does not edit the released generator or use the scored
collector. Run from the repository root:

```bash
python studies/coverage-search-v1/screen.py --out artifacts/coverage-search.json
```

Elapsed times depend on the machine; deterministic case hashes, outcomes and
state counts are the reproducibility targets.

## Next acceptance gate

1. Retain all four released anchors and freeze candidate structures before
   further tuning. Reserve different structures and fresh seeds for validation.
2. Check constructive solvability, bounded public-reference runtime, relevant
   heuristic rescue ablations and recovery behavior on the candidates. Preserve
   search failures; do not silently filter the generator to reference-friendly seeds.
3. Compare direct-model and explicitly solver-assisted configurations separately,
   with declared computation and transport budgets. These current model adapters
   expose no external solver; do not imply that tool-augmented agents were tested.
4. Only promote scales after completed strong-model outcomes demonstrate a useful
   region between ceiling and floor under the sample/precision requirements in
   the [difficulty contract](../../docs/DIFFICULTY.md). More than 5,000 states is
   a development signal, not a promotion rule.
