# Development roadmap — useful delivery first

[中文](ROADMAP.zh-CN.md) · [Design](DESIGN.md) · [Repair contract](REPOSITORY_REPAIR.md)

Build a durable, difficult evaluation of agents delivering useful work under
partial observability. Actual accepted outcomes drive development. Scientific
controls diagnose failures; they must not indefinitely postpone the application.

## Question, delete, simplify

Apply **question → delete → simplify/optimize → accelerate → automate**.
Each addition needs a concrete outcome, an acceptance check and a removal condition.
Make bounded decisions, execute them, retain failures and revise from evidence.

| Assumption | Decision |
|---|---|
| Larger synthetic catalogues ensure lasting difficulty | Stop mainline expansion; preserve existing versions as controls |
| Compression and more synthetic qualification must precede real work | Delete that dependency; implement real delivery now |
| Real repair requires a general shell and a new execution framework | Seven bounded actions, existing collector/evidence path |
| Exit code zero proves repair | Compare behavior against an evaluator-owned oracle |
| Upstream patch is an agent baseline | Artifact control only |
| One public issue establishes frontier difficulty | Execution fixture first; difficult task portfolio next |
| Uncertainty forbids decisions | Choose a reversible implementation and test its consequences |

## Active route

```text
R0: real repair → isolated execution → regression acceptance → patch
  → R1: difficult real tasks with cross-file constraints and recovery
  → R2: strong-model delivery and measured human review burden
  → R3: expand useful tasks; optimize measured bottlenecks
```

This supersedes the old P0–P5 implementation dependency. Synthetic and mechanism
studies remain available with unchanged evidence. Prospective prediction remains
a research question, not a prerequisite for executing real work.

### R0 — First real delivery loop

Implemented in 2.7: pinned pre-fix packaging source, bounded inspection/edits,
fresh-container execution, 118 behavioral checks, current verification, explicit
finish, patch and evidence. [Six fixed controls](../studies/repository-repair-v1/README.md)
test the boundary and repeat actual executions.

Acceptance: upstream repair passes; unchanged/example-only repairs, tampering,
stale verification and empty exit-zero fail. Preserve all rows, source/runtime
identities and recheck discrepancies. Response fixtures alone do not close this gate.

Delete infrastructure unrelated to executing tasks, grading relevant behavior or
retaining failures. No retries, plugin registry, database or model ranking.

### R1 — Difficult, valuable real tasks

**R1a implemented:** three independently sourced real defects
with multi-file behavior or interacting compatibility requirements. Pin each
before-state, describe the concrete user failure, specify executable acceptance,
retain an accepted upstream solution as an artifact control, and construct a
plausible partial repair that fails a related regression.

The 2.8 routing, initialization and response-reading tasks pass twelve artifact
controls and fresh rechecks. Missing build metadata and an ineffective smoke
example were corrected with all earlier results retained. The
[six-proposal baseline](../studies/repository-portfolio-v1/proposal_plan.json)
explicitly supplies localization help and tests patch construction. It does not
replace an interactive evaluation.

**R1b next: autonomous localization and recovery.** With execution available,
compare problem-only versus file-localized conditions on identical tasks and
budgets. Require plausible incomplete repairs, obtainable evidence and executable
regression constraints. Retain easily repaired cases as regression anchors;
do not manufacture difficulty by enlarging catalogues or hiding acceptance requirements.

Freeze tasks and budgets before model attempts. Run available Sol and GLM
configurations on the same tasks with useful tools. Retain all attempts, including
transport/execution failures. Use observed failures to choose the next change.

Acceptance: actual patches, preserved related behavior, and measured separation
or saturation of strong configurations. If all solve easily, retain regression
anchors and choose harder consequential work. If tools cause all failures,
repair tooling before claiming difficulty.

Remove tasks whose difficulty comes only from formatting, missing dependencies,
long payloads or forbidding useful tools. Public historical fixes are development
material. Reserve independent task sources for evaluation; never relabel known
tasks as held out.

### R2 — Delegation value

On unseen tasks, measure accepted patches, reviewer time, requested corrections
and unassisted completion. Specify ownership, acceptance and a practical baseline
before collection. Compare useful outcomes and total costs.

Acceptance: independent tasks sufficient for the declared operational decision,
with uncertainty and failures visible. Publish negative results and narrow the
application when expected value is absent. Synthetic score correlations are
optional diagnostics. Never replace measured human effort with simulated steps.

### R3 — Scale useful parts

Profile model input, execution and review costs. Delete repeated work, optimize,
then introduce scheduling or recurring evaluation only when needed. Increase
difficulty as models improve while retaining immutable anchors and evidence bindings.

## Evidence retained

The [depth pilot](../studies/coverage-depth-v1/README.md) retains two open request
timeouts and two assisted successes. A fixed tool-consumer solves all 24 qualified
cases. This motivates the mainline change without proving model incapability.

[Collection](COLLECTION.md), [study](STUDIES.md), [diagnostic](SPECIFICATION.md),
[discovery](DISCOVERY_RECOVERY.md) and [coverage](DIFFICULTY.md) contracts remain
regression constraints. Published failures are preserved. Source-task clusters
and synthetic seed clusters stay distinct. Hashes verify consistency, not a
hostile evaluator's honesty. Missing measurements remain unknown.
