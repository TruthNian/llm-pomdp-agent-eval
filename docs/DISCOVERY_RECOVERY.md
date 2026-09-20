# Discovery and recovery — offline contract 1

Status: an executable development prototype, **not a registered scored family**.
Contract version: `dependency-recovery/1`. The diagnostic generator, prompts,
grader and historical studies keep their existing semantics.

## Question, deletion and smallest useful experiment

Does a policy acquire a previously unavailable operation and revise its work when
an announced dependency replacement invalidates that operation and an earlier
successful verification? The current diagnostic kernel cannot represent this
through a new candidate label alone: it needs changing operation availability,
invalidation of completed work, and a transition back from verified progress.

Keep one goal and one active dependency. Delete random generation, extra graph
depth, domain skins, provider calls, prompt conditions, aggregate scores and a
second durable collector from this iteration. Use fixed public development
fixtures and observation-only controls to test the contract first.

This is not discovery of an arbitrary hypothesis space, unknown transition-law
learning, a stochastic external-change model, or evidence of real-work validity.
The operation rules and replacement timing are deliberately disclosed.

## World and public boundary

The evaluator owns two distinct dependency handles: the initial handle and its
replacement. Only one is required at a time. There is one final deliverable.
Preparing a dependency and assembling the deliverable each cost 2; probing and
verification each cost 1. Every fixture has **12 action points and 20 steps**,
independent of handle identities and the two ablations.

Initially the dependency is either disclosed (discovery ablation) or unknown.
`probe` reveals the current handle, making its preparation operation available.
Guessing a hidden or future handle never grants access; the same invalid-action
response is returned for any undisclosed handle. This is a simulator action
availability rule, not a cryptographic or operating-system capability boundary.

The public observation includes remaining resources, world revision, last
observed dependency handle, whether that evidence is stale, prepared dependency,
assembly provenance, and the last action result. It never includes the fixture,
unrevealed handle, future handle, acceptance state or evaluator files. Stored
traces include public development fixtures for replay; policies receive only the
contract, current observation and public history. In-process controls are trusted
code, as in the released runner.

## Transitions

Actions use `{"command": "..."}` with `target` only for `prepare`.

| Action | Points | Result |
|---|---:|---|
| `probe` | 1 | Reveal/refresh the current dependency handle; do not mutate the world |
| `prepare HANDLE` | 2 | Prepare a previously observed, current handle; increment revision |
| `assemble` | 2 | Requires current dependency evidence and preparation; create an assembly with that provenance; increment revision |
| `verify` | 1 | Check current preparation and assembly; on PASS record the checked revision |
| `status` | 0 | Read public state |
| `finish` | 0 | End irreversibly; acceptance is evaluated on the resulting state |

Invalid, stale, unmet-prerequisite and unaffordable actions cost no points and
consume one step. All other actions, including `status` and `finish`, also consume
one step. Repeating a mutation invalidates verification even if its value does
not change. Blocked actions never mutate the world.

In the changing fixture, the **first passing verification** is immediately
followed by exactly one dependency replacement in the same transition. The
response reports PASS for the old checked revision and an explicit change event
with the new world revision. The observation marks cached dependency evidence
stale. It retains the old preparation and assembly as obsolete work, withholds
the replacement handle until `probe`, and invalidates verification. No further
replacement occurs. The contract tells the policy about this timing in advance;
there is no undisclosed requirement to predict a surprise event.

Accepted completion requires explicit `finish`, preparation and assembly for the
current dependency, verification at the latest revision, and both budgets. A PASS
followed by replacement is not acceptance. The final permitted step may be
`finish`. Merely reaching the step limit terminates unsuccessfully.

## Constructive witness and costs

The adaptive witness reads public JSON only:

1. Probe if dependency information is absent or stale.
2. Prepare the observed current dependency if necessary.
3. Assemble if the deliverable has different/missing provenance.
4. Verify, then finish only if PASS refers to the current revision.

After replacement the same rule reacquires the handle and rebuilds. Hidden /
changing takes `probe, prepare, assemble, verify` twice, then `finish`: **12
points, 9 steps**. Visible / changing takes 11 points; hidden / stable 6; visible /
stable 5. This is a constructive solvability bound, not a global policy optimum.

## Falsifiable controls

The complete matrix crosses discovery (visible/hidden) and replacement
(stable/changing), with three explicitly public handle-pair fixtures. Two pairs
share their initial handle but differ in their future handle, supporting a
counterfactual check that future identity cannot affect earlier observations.
Handle relabelings are engineering fixtures, **not independent research samples**.

| Control | Visible / stable | Hidden / stable | Visible / changing | Hidden / changing |
|---|---:|---:|---:|---:|
| `adaptive` | PASS | PASS | PASS | PASS |
| `static` — freeze actions from initial information | PASS | FAIL | FAIL | FAIL |
| `never_revise` — discover once, stop after first PASS | PASS | PASS | FAIL | FAIL |
| `premature_finish` — deliver immediately after assembly | FAIL | FAIL | FAIL | FAIL |
| `overprobe` — spend all resources investigating | FAIL | FAIL | FAIL | FAIL |

Each intended obstacle has an ablation that rescues the relevant failing control.
The checker verifies all 60 planned trajectories, policy actions, replayed
observations/grades, exact matrix coverage and an acceptance check based on public
history implemented separately from the environment's state-based grader. It
retains failed controls and reports costs without confidence intervals, model
rankings, provider usage estimates or a pooled autonomy score.

`unresolved_dependency` marks an unavailable prerequisite; it does not classify a
first exploratory attempt as an avoidable mistake. `stale_dependency` is issued
only for a previously revealed handle after an announced replacement.
`redundant_probes` counts deterministic probes while the current handle is already
known. None of these labels infers an agent's intent.

## Run and migration

```bash
python -m pomdp_bench.discovery_controls --out artifacts/discovery-controls.json
python -m pomdp_bench.discovery_controls --validate artifacts/discovery-controls.json
```

The output is a complete offline control report, not a scored-suite manifest. An
existing file is never overwritten, including concurrent creation. An interrupted
offline write can leave an invalid file; choose a new output path. The report
cannot enter `prepare-study`, `resume`,
the model runner, or diagnostic summaries. No network requests are made.

This prototype has its own version; any change to its observations, transitions,
controls or acceptance requires a new version and reviewed control evidence.
Adding source files changes the released collector's source fingerprint; ongoing
diagnostic collections must resume in their original checkout. Historical replay
and frozen evidence remain unchanged.

## Decision gate

Retain this structure only if the witness succeeds under every ablation, the
targeted failures disappear when their corresponding obstacle is removed, hidden
handles do not leak, completed work really becomes obsolete, and both acceptance
implementations reject stale verification. Otherwise simplify or remove it.

Passing this gate supports the narrowly defined prototype contract. It does not
complete P3. The next gate is a bounded generator with meaningful structural
variation, public-information solvability for every generated case, and reuse of
the existing collector/replay path without importing diagnostic-only metrics.
Before implementing it, challenge whether variation adds decisions rather than
just identifiers. The live transport gate, mechanism studies and external
validation remain separate and open.
