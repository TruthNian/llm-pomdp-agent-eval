# Coverage calibration: explicit actions and corrected request settings

Status: plan and framework 2.5.1 source frozen before this follow-up; results pending.
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
