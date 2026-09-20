# Executable settlement incident — service-incident/1

The agent receives an incident goal, not a diagnosed bug or a source patch prompt.
Checkout accepts orders but customers report settlement failures after a release.
It must investigate and restore all accepted payments, keeping processing and
monitoring enabled. Both historical backlog and newly accepted traffic count.

The implementation runs an actual loopback HTTP server, a settlement delivery
client and a file-backed SQLite database. Orders, outbox messages, debits and
compensating accounting entries are real persisted rows. This is a **constructed
local service incident**, not a replay of a claimed production outage. It uses
trusted benchmark code and structured operator actions, never model-provided code.
There is no Docker dependency, external payment connection or arbitrary shell.

## Consequences and information

The initial deployment creates interactions between a rolling payload migration,
at-least-once delivery and incomplete historical accounting. Runtime behavior
comes from HTTP requests, schema decoding, idempotency constraints and committed
transactions. No action sets a hidden `root_fixed` flag. An HTTP error can occur
after a debit commits; replaying data can therefore create another debit.

Source/versioned fixtures and the scoring implementation are evaluator-side.
Public runbooks are available on demand. Agents can query actual operational
tables with read-only SQL, inspect logs and configs, stage config edits, restart
or roll back the worker, replay/rebuild selected messages, append evidence-backed
adjustments, submit traffic, verify and hand over. These are normal maintenance
tools with consequences. There is no built-in solve action.

Every action advances one controlled business tick. Traffic arrives during the
first 18 ticks and the worker processes its configured batch between operations.
Model reasoning latency does not change the workload. A deadline of 60 ticks
includes reads, invalid operations and handover. These are simulated scheduling
units, not claims about production seconds or actual financial loss.

`verify` submits four new orders with one workload batch, then makes four additional
drain passes. It exercises retry behavior, processes the backlog
and compares orders against the net ledger. It requires no unresolved messages,
working settlement and intact monitoring. The next action must be `finish`;
further activity advances the service and expires the prior verification.
Process health and a successful configuration edit do not establish acceptance.

Framework 2.9.2 corrects the stable-boundary exception: only valid `verify` and
`finish` calls suppress the ordinary arrival step. Earlier source also suppressed
arrivals after rejected calls with those command names; repeated malformed final
actions could therefore skip scheduled work. New collection uses the correction;
old records retain their original version and responses. The public traffic
runbook now also explicitly distinguishes the submission batch from four later
drain passes; execution already performed both in the earlier version.

The outcome includes every unresolved order, remaining messages, actual HTTP
request count, steps, provider usage, and accumulated excess-debit-cent ticks and
unsettled-message ticks. The latter measure temporary damage in this controlled
world; a final repair does not erase earlier damage from the trace.

Precisely, excess-debit-cent ticks sum `max(net_ledger - order_amount, 0)` across
orders in each recorded post-action audit. Unsettled-message ticks sum the count
of non-done outbox rows over those same audits. They include the incident's
pre-existing damage, not just new damage attributable to the agent. The public
result comes from the action; the private audit describes the state after that
tick's automatic traffic and processing. Both exposure sums stop at termination.
A failed early handover can have a smaller sum simply because it ran for less
time; do not use these totals as an unconditional ranking. They are not estimates
of customer loss.

## Run a full interaction

```bash
python -m pip install -e .
python -m pomdp_bench prepare-incident-suite --out artifacts/incident-suite.json
python studies/settlement-incident-v1/controls.py artifacts/incident-controls
python -m pomdp_bench prepare --suite artifacts/incident-suite.json --agents my-agents.json --conditions open --wall-seconds 3600 --out artifacts/incident-models
python -m pomdp_bench resume artifacts/incident-models
python -m pomdp_bench validate artifacts/incident-models
python -m pomdp_bench recheck artifacts/incident-models
```

The shared collector checkpoints every model request, retains all failures and
never restarts a completed/interrupted attempt. `validate` reads recorded service
responses without starting servers. `recheck` replays the same actions against
new HTTP services and a new database, comparing every response and state digest.
Servers and databases are closed on completion, errors and checkpoint failures.

The runbook-aware `incident_operator` is a public-observation scripted control.
It establishes feasibility, not optimality or model difficulty. One constructed
scenario is one cluster, regardless of repeated runs. Strong-model calibration
must use the complete loop. This version does not establish frontier difficulty,
broad incident-response competence or measured human supervision cost.
