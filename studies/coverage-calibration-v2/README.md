# Coverage calibration: explicit actions and corrected request settings

Status: **all four attempts retained and replayed; three successes and one
transport-size failure. Frontier difficulty and model discrimination remain unproven.**
The source and plan were public at
[`6271570`](https://github.com/TruthNian/llm-pomdp-agent-eval/commit/627157092ab939c44524ef9b8a7d4c02a94ce6cb)
before preparation and requests. Framework 2.5.1 source fingerprints matched
through collection and evidence export.
The [first pilot](../coverage-calibration-v1/README.md) remains four failed attempts.

The follow-up deletes the optional output cap implicated by a separate fixed pair
of public constant-output probes. It also makes action syntax explicit in the
versioned task contract and supplies useful feedback for invalid schemas. Work
constraints and generated graphs are unchanged. A 600-second request limit and
2,400-second episode limit give these high-reasoning configurations more time;
time/format changes prohibit attributing differences to model improvement.

The [plan](plan.json) fixes GPT-5.6 Sol and GLM-5.3, public seed zero, `sanity` and
`extreme`, high reasoning, one attempt each: four episodes. No added seeds, retry,
replacement of failures or post-preparation changes. This uses the same public
development inputs, not independent samples or private held-out evaluation.

The [launcher snapshot](launcher.py) binds the plan to the ordinary collector and
scopes existing credentials to these requests. It does not change global auth,
router settings or sharing consent. No provider response bodies, reasoning or
credentials are published. The reference agent uses only public observations;
the model receives no reference plan, seed or future matrix.

```bash
python studies/coverage-calibration-v2/launcher.py prepare artifacts/cover-followup
python studies/coverage-calibration-v2/launcher.py collect artifacts/cover-followup
python -m pomdp_bench validate artifacts/cover-followup
```

Every attempt must replay and remain visible. Only completed task outcomes can
inform headroom; transport/deadline failures leave capability unknown. Even a
successful small-versus-large separation is only a development signal. Readiness
requires the independent sample and precision gates in the [difficulty contract](../../docs/DIFFICULTY.md).
Real-work transfer and training/parameter-scale causes remain unestablished.

## Complete results

| Configured model | Scale | Applied actions | Outcome | Seconds |
|---|---|---:|---|---:|
| GPT-5.6 Sol | sanity | 7 | Accepted completion | 22.51 |
| GLM-5.3 | sanity | 7 | Accepted completion | 19.65 |
| GLM-5.3 | extreme | 1 | Response exceeded 2,000,000 wire bytes | 401.37 |
| GPT-5.6 Sol | extreme | 7 | Accepted completion | 206.19 |

[All four outcomes](live-evidence.json) include 23 independently reconstructed
request fingerprints and 22 complete usage reports. The failed GLM attempt only
probed the catalogue; it applied no build. Its total usage stays unknown. It is
a retained operational failure, not evidence that the model cannot solve the task.
The configured GLM alias and returned model label were unequal; immutable upstream
checkpoint identity is not attested. The launcher's before/after check confirmed
unchanged global auth, router settings and sharing-consent bytes.

Sol's successful extreme run spent exactly the allowed 15 work units across
both epochs. Reported totals were 109,034 input and 10,560 output tokens, including
10,396 reported reasoning tokens. These are provider counters across complete-history
requests, not unique prompt length, FLOPs or a price estimate. The 206-second
completion is a cost observation on one public task; success at the highest
released scale does not establish its population ceiling or durable headroom.

The [specialized-solver screening](../coverage-search-v1/README.md) provides a
second counterexample to assuming that scale names mean high difficulty. It
motivates deeper compatibility structures and solver-assisted baselines before
declaring a broad agent benchmark ready.

## Correction after this frozen collection

Framework 2.5.2 makes the response byte limit an explicit, bounded HTTP-agent
configuration and records the selected value in each request audit. The default
remains 2,000,000 bytes. A local completed-reasoning-stream fixture above that size
succeeds with a larger declared allowance, while a one-byte-smaller allowance
still fails. No provider retry or third model calibration is included here.
The change is fixture-validated; it does not establish that the failed GLM
attempt would have succeeded under different settings.
