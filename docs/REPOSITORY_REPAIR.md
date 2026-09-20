# Real repository repair — repository-repair/1

Framework 2.8 additionally registers `repository-repair/2`, the
[three-task compatibility portfolio](../studies/repository-portfolio-v1/README.md).
It reuses this state machine with task-specific source and behavioral checks,
80 steps and 12 executions. Existing Python source/type stubs under src/ are
writable; public docs/tests remain read-only. Select it explicitly with
`prepare-repair-suite --tasks werkzeug_routing attrs_preinit urllib3_read`.
The original packaging contract and its recorded replay are preserved.

Framework 2.7 adds an executable repair task over real upstream code. The output
is a unified source patch. Acceptance checks behavior in an isolated runtime,
requires verification of the current revision, and requires explicit handover.
The shared collector retains every attempt and its execution failures.

## First task and scope

[pypa/packaging issue 1204](https://github.com/pypa/packaging/issues/1204) reports
that pickling a Requirement loses an explicitly configured prereleases setting.
The fixture pins the pre-fix commit
`20262cf73c9a3b55eea0ce305fb5a8111911ef3c`: complete package source plus selected
public tests, docs and licenses, 32 files. It is a selected source snapshot, not
the full Git checkout. Per-file hashes and upstream provenance are stored in
[the fixture](../pomdp_bench/repair_data/packaging_state/provenance.json).

The upstream repair is an evaluator-only **artifact control**, establishing that
the behavioral contract admits a delivered fix. It is not an observation-only
policy, a model attempt, or evidence of frontier difficulty. The public historical
issue is an execution acceptance fixture. Difficult real tasks are the next
development work; repeatedly increasing this fixture's size is not.

## Interaction and acceptance

The model initially sees the issue, action schemas, limits and compact status.
Source details become available through deliberate reads and literal searches.
It never receives the upstream fix, private case identifier, grader source,
container image ID or future outcomes. Each edit invalidates prior verification.

| Action | Effect and limit |
|---|---|
| `list` | List available paths |
| `read` | Read 1–200 lines of a selected file |
| `search` | Literal search; first 30 matching lines |
| `edit` | Replace one unique exact string in an existing src/packaging Python file |
| `test: reproduction` | Execute the reported example |
| `verify` | Execute all 118 behavioral checks |
| `finish` | Irreversible handover of the current patch |

There are 40 action steps and 8 code-execution calls. Invalid/blocked actions
consume steps; failed executions consume checks. Each check starts a fresh
container. There is no shell, package installation or external network action.
Public tests and docs are read-only. Agent edits cannot modify the acceptance
oracle. A successful handover needs a nonempty patch and a full PASS after the
latest edit. Passing only the reported example is insufficient.

The oracle covers protocols 0–5, shallow/deep copy, explicit True/False/automatic
None, four requirement forms, existing string state, legacy dictionary state,
and invalid states. It compares absolute object fields, including raw and
effective prerelease settings. It does not require the upstream patch's syntax
or exact serialization format. This is a targeted regression suite; the entire
upstream test suite is not executed. Legacy dictionaries are reconstructed in
the pinned package, not collected from every historical binary pickle.

## Execution and evidence

Candidate source is never imported by the evaluator. A stdlib worker runs inside
Docker, receives source and behavioral inputs, and returns JSON values. Expected
values remain in the evaluator. A zero exit code or a claimed PASS is insufficient.

The runtime uses an immutable local image ID, no automatic pull, no host mounts,
no forwarded credentials, no network, a read-only root, an unprivileged user,
no Linux capabilities, and a 32 MiB temporary workspace. Each execution has a
20-second deadline, 256 MiB memory, one CPU, 32-process and 256 KiB output limits.
Timeout cleanup explicitly removes the container. Docker is a required external
runtime; absent Docker is an execution failure, never a host-execution fallback.

These controls isolate execution and protect the evaluator-owned oracle. They
do not attest an honest Docker host or prove resistance to source deliberately
spoofing the worker's measurement channel. The six controls test specified
failure modes; no comprehensive adversarial-hardening claim is made.

Each execution record binds its source snapshot, revision, check inputs, check
version and image ID to the returned values. Traces contain the final patch.
Source-task identity defines the statistical cluster; repeated runs of this
single issue do not become independent tasks. Optimal action cost is unknown
and reported as null. Tool steps, check calls, edited files, execution failures,
elapsed time and provider-reported usage are separate measurements.

- `validate` replays edits and regrades **recorded** behavior, without Docker.
- `recheck` executes checks again in fresh containers using the pinned image,
  compares results with the original evidence, and never overwrites that evidence.
- `resume` retains completed/interrupted attempts, collecting only unstarted ones.

Hashes establish consistency, not independent attestation of execution.

## Run

On a machine with Linux Docker containers available:

```bash
python -m pip install -e .
docker pull python:3.13-slim
IMAGE=$(docker image inspect python:3.13-slim --format '{{.Id}}')
python studies/repository-repair-v1/controls.py --image "$IMAGE" --out artifacts/repair-controls
python -m pomdp_bench validate artifacts/repair-controls
python -m pomdp_bench recheck artifacts/repair-controls
```

The control command includes its own fresh execution recheck. The last command
demonstrates repeating that audit. Record the resolved image ID and repository
digest, rather than treating the mutable image tag as a reproducibility guarantee.

For a model, configure a `chat` or `responses` agent through the existing
[HTTP adapter](MODEL_ADAPTERS.md), then:

```bash
python -m pomdp_bench prepare-repair-suite --image "$IMAGE" --out artifacts/repair-suite.json
python -m pomdp_bench prepare --suite artifacts/repair-suite.json --agents my-agents.json --conditions open --wall-seconds 1800 --out artifacts/repair-models
python -m pomdp_bench resume artifacts/repair-models
python -m pomdp_bench validate artifacts/repair-models
```

Select wall/provider budgets before attempts. Only `open` is supported. The
`actions` policy executes fixed artifact-control sequences; it must never be
reported as a model or public-information solver. The pinned suite contains one
source task and has no fabricated random seed or difficulty ladder.
