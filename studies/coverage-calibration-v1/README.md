# Coverage difficulty calibration 1

Status: the implementation and [four-episode public pilot plan](plan.json) are
frozen before live collection. No model-difficulty or ranking conclusion yet.

The [difficulty contract](../../docs/DIFFICULTY.md) introduces a structural ladder
and makes measurable headroom a readiness requirement. P3.1 remains a small
contract test; its reactive-policy success did not establish a hard benchmark.

## Offline development controls

Public seeds 0–11 × four scales × four scripted policies: **192 episodes**.
Every episode was retained and replayed through the existing collector. These
are engineering controls across a declared generator, not model scores.

| Policy | sanity | challenge | hard | extreme |
|---|---:|---:|---:|---:|
| Public-information exact reference | 12/12 | 12/12 | 12/12 | 12/12 |
| Maximum new coverage | 5/12 | 0/12 | 0/12 | 0/12 |
| Rarest goal first, then maximum coverage | 11/12 | 1/12 | 0/12 | 0/12 |
| Exact initial plan, no recovery | 0/12 | 0/12 | 0/12 | 0/12 |

The reference discovers rows, finds compatible operations, preserves unaffected
work, rediscovers expired descriptions and restores changed goals. It succeeds
in seven requests at every scale because batch actions preserve resource costs.
Heuristic failure is about choices under work limits, not added API-call count.

Independent tests compare the public solver against exhaustive enumeration on
150 small random set systems. Tests also check seed-independent resource bounds,
atomic batches, hidden future information, selective invalidation, old-version
rejection, shared interruption/resume, and null diagnostic-only metrics. Relaxing
work allowance rescues the local heuristics on the tested hard fixture; removing
replacement rescues the non-revising control. These are targeted ablations.

Reproduce the complete offline matrix:

```bash
python -m pomdp_bench generate-cover --seed 0 --count 12 --scales sanity challenge hard extreme --out artifacts/cover-suite.json
python -m pomdp_bench run --suite artifacts/cover-suite.json --agents examples/coverage-agents.json --out artifacts/cover-controls
python -m pomdp_bench validate artifacts/cover-controls
```

## Fixed public model pilot

One public development seed, `sanity` and `extreme`, GPT-5.6 Sol and GLM-5.3: four
episodes, each attempted once. Both use high reasoning, a 16,384 output-token
ceiling, 240-second request deadline and 1,800-second episode deadline. Existing
credentials remain in process memory; global routing/consent/auth files are not
changed. The [launcher](launcher.py) prepares the complete matrix and binds the
plan before any requests. Run it from an editable installation of the frozen
source; the generic benchmark never discovers credentials.

```bash
python studies/coverage-calibration-v1/launcher.py prepare artifacts/cover-live
python studies/coverage-calibration-v1/launcher.py collect artifacts/cover-live
python -m pomdp_bench validate artifacts/cover-live
```

This bounded diagnostic uses public inputs because the installed route's earlier
all-four gate failed. No private scoring case is spent debugging transport.
Channel failures stay in the denominator and provide no evidence about planning
ability. No result-dependent retry, extra seed, timeout change or replacement is
permitted. Code changes require a new source-bound collection.

Even completed success/failure differences on this one seed are only development
signals. The next discrimination gate needs independently frozen private seeds,
declared precision, multiple model/compute settings and explicit ceiling/floor
checks. No parameter-scale, training-mechanism or real-work claim follows here.
