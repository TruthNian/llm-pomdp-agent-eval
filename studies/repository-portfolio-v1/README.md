# Three real compatibility repairs — fixed development matrix

The purpose is executable selection of real tasks with consequential surrounding
constraints. Task count and public provenance do not establish high difficulty.
These are public development issues, not held-out evaluation.

| Task | Actual user failure | Acceptance coverage |
|---|---|---|
| [Werkzeug 2834](https://github.com/pallets/werkzeug/issues/2834) | Disabled slash merging still redirects an existing route | 166 checks: Map updates, rule overrides, converters, redirects, methods and literal slashes |
| [attrs 1427](https://github.com/python-attrs/attrs/issues/1427) | Pre-init hook sees defaults instead of supplied arguments | 37 checks: defaults/factories, positional/keyword calls, aliases, converters, slots/frozen, omitted or absent hooks |
| [urllib3 3636](https://github.com/urllib3/urllib3/issues/3636) | Partial then complete response read loses decoded bytes | 126 checks: real Brotli/gzip/deflate, raw bytes, partial/full reads, EOF, caching and byte order |

Source snapshots contain complete package Python source/type stubs and selected
pre-fix docs/tests. The [import script](../../tools/import_repair_portfolio.py)
reproduces per-file provenance and upstream source patches without executing
candidate code. Upstream artifacts are acceptance controls, never model attempts.
The original packaging fixture and its published evidence remain unchanged.

## Fixed controls and runtime

Before any execution, [controls.py](controls.py) defines three tasks × four
controls: unchanged, partial repair, complete upstream artifact, and a later
unverified edit. Every task has 80 steps and 12 check calls. The collector has
300 wall seconds per artifact trajectory. Original attempts are never replaced.

Only the upstream artifact should deliver. The partial repair must pass the
reported reproduction but fail complete acceptance:

- Routing: repair the Map setter but omit the per-rule constraint.
- Initialization: forward required/default arguments but omit the factory branch.
- Response reading: drain the old buffer but discard newly decoded bytes.

Fresh-container rechecks are additional audits of the same recorded actions,
not replacement scores. A gate failure retains its matrix and discrepancies.
These finite checks do not establish all-library correctness or comprehensive
resistance to malicious measurement spoofing.

[Dockerfile](Dockerfile) extends the pinned Python base with MarkupSafe 3.0.3 and
Brotli 1.2.0 before candidate execution. The resolved image ID binds each case.
The candidate has no network, host mount, credentials or installation action.
The worker explicitly loads the container's dependency directory with site
startup disabled. It returns behavior values; expected answers remain outside.

```bash
docker build -t pomdp-repair-portfolio studies/repository-portfolio-v1
IMAGE=$(docker image inspect pomdp-repair-portfolio --format '{{.Id}}')
python studies/repository-portfolio-v1/controls.py --image "$IMAGE" --out artifacts/portfolio-controls
python -m pomdp_bench prepare-repair-suite --image "$IMAGE" --tasks werkzeug_routing attrs_preinit urllib3_read --out artifacts/portfolio-suite.json
```

Use the ordinary prepare/resume workflow with HTTP agents and condition open.
Validation regrades recorded values without importing candidate code. Runtime
availability is a prerequisite for scored interactive model runs.

## Status

**Final qualification passed** at clean source
`42ffa1a73b83a2417620ff6551396448fab5acfa` in
[CI run 35498639649](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35498639649).
All twelve rows, eighteen original executions and eighteen fresh rechecks are
retained in [control-evidence.json](control-evidence.json).
[execution.json](execution.json) binds source, image, dependencies and evidence bytes.

| Task | Unchanged full checks | Partial repair full checks | Upstream full checks |
|---|---:|---:|---:|
| Werkzeug routing | 148/166 | 154/166 | 166/166 |
| attrs initialization | 28/37 | 25/37 | 37/37 |
| urllib3 reading | 114/126 | 118/126 | 126/126 |

Every unchanged source fails its reproduction; every partial repair passes
reproduction but fails full acceptance. Later edits expire all earlier PASSes.
All fresh rechecks agree. Run `python studies/repository-portfolio-v1/verify.py`
to regrade the recorded final matrix without candidate execution.

## Frozen model screen

[proposal_plan.json](proposal_plan.json) declares six single-proposal attempts,
two user-authorized models on the three public tasks. Source context deliberately
includes known affected files and neighbors: this baseline has localization help.
It measures construction of a patch from that context, not autonomous repository
localization, interactive recovery, or end-to-end POMDP completion.

Model calls run locally through the existing HTTP adapter. Only reviewed patch
artifacts reach CI for independent execution; no provider credentials are sent
to CI. There is no test feedback, correction or replacement attempt. Missing
usage and failed/interrupted requests remain visible. Calls start only after the
artifact gate and publication of the plan/source.

All six requests have completed under clean prepared source
`b4eb5cf9eb9424f7aee7fe276b18dc8b7c253f08`.
[model-proposals.json](model-proposals.json) retains five valid submissions and
one 600-second request timeout; no retry or correction was made. All six request
fingerprints were verified. Local configuration and authentication bytes were
unchanged. Independent container acceptance is pending.

Sol completed all three requests and reported the requested model name. The two
completed GLM-routed requests did not report an exact match to the requested
`custom/z-ai/glm-5.3` alias. The adapter retains that mismatch, not an independently
verified provider identity. The timeout has unknown usage, not zero usage.

## Development corrections retained

The [first CI attempt](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35498144035)
at source `4974c51a2f45c328422cea87c0f5e5e6570a2f14` stopped during image build:
BuildKit interpreted a local image ID as a registry name. Zero of the twelve
portfolio trajectories executed. The original packaging controls passed.
The correction removes the build argument and pins the base repository digest
directly in the Dockerfile. This infrastructure failure is retained; it is not
a task or model failure.

The [first complete execution](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35498206690)
retains all twelve rows in [first-execution-failed.json](first-execution-failed.json).
Routing and initialization separated correct and partial repairs as intended.
All urllib3 checks returned ModuleNotFoundError: its untracked _version.py is
normally generated by the upstream build backend and was missing from the source
snapshot. The fixture now explicitly includes generated build metadata with
version `0+benchmark`, separately fingerprinted from upstream files. No test
oracle was relaxed. This is an environment correction before model collection.

[The next execution](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35498449431)
passed full acceptance for all three upstream patches and rejected all partial
repairs. Its complete [initial screen](initial-reproduction-screen.json) is retained.
Inspection found that urllib3's nine-byte smoke example also passed unchanged
code, despite 12 genuine failures in the full suite. Before model collection,
the reproduction selection was changed to an already-existing 20,000-byte
Brotli case with reads of 512 and 1024 bytes, where unchanged code fails and
the partial repair passes. The 126 full checks are unchanged. The gate now
requires unchanged code to fail the reproduction for every task.

The corrected read-check contract is `urllib3_read/2`; the earlier development
matrices retain `urllib3_read/1` and their original source commits.

[Cross-version CI](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35498753295)
then found that host-generated gzip headers differ between Python 3.11 and 3.13,
so recorded raw-read inputs could not be replayed across versions. Python 3.12
reproduced the mismatch locally. The correction stores the six compressed wire
inputs verbatim, preserving every byte of the successful Python 3.13 execution.
It changes neither acceptance nor the already-frozen model requests. Candidate
decoding still executes in the pinned container. This compatibility correction
was applied only after the six model attempts and their source bindings were exported.
