# Stream recovery after a destructive failback

Framework 2.15 development candidate; generator `stream-recovery/1`, runtime
`postgres-debezium-kafka/1`. This evaluator document is outside the operated environment.
The high-difficulty objective remains unproved until complete strong-model attempts
and causal checks provide the relevant evidence.

## What changed from the rejected merge task

The previous candidate retained two complete live databases. A paused writer and
conflict-free union solved it. Merely inserting Kafka would preserve that shortcut.
This candidate starts after an actual `pg_rewind` has overwritten the old branch.
The surviving ordinary base backup and archived WAL can reconstruct it. No grading
flag simulates the loss, and no evaluator restoration is offered to the agent.

The causal adaptation combines divergent acknowledged writes, an operator's unsafe
failback, and downstream work that survives the database rewind. GitHub's
[2018 incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)
describes divergent writes, the decision to avoid unsafe failback, and recovery of
backlogs. GitHub used MySQL; it did not report this PostgreSQL/Debezium deployment or
the specific unsafe rewind constructed here. This is an adaptation, not a production reproduction.
[PostgreSQL documents pg_rewind](https://www.postgresql.org/docs/17/app-pgrewind.html)
as timeline resynchronization, not business-record merging.
[Debezium's PostgreSQL connector](https://debezium.io/documentation/reference/3.2/connectors/postgresql.html)
tracks replication state separately from application rows.

## Actual processes and state

The image runs PostgreSQL 17, Kafka 4.0.0 and Debezium 3.2.1.Final from resolved
upstream image digests. An ordinary commerce API persists customer requests, order
state and an outbox in one transaction. Kafka Connect captures actual PostgreSQL
changes; a Kafka consumer dispatches released orders. Consumer offsets, connector
offsets, replication slots and local dispatch receipts are real persisted state.

The local carrier is a constructed HTTP service, not a commercial integration. Its
append-only dispatch ledger resides in a separate container volume. The operated
container receives neither that filesystem nor a Docker socket. Its merchant API
supports idempotent booking and lookup, with ordinary discoverable documentation.
New bookings commit records that application edits cannot delete or refund.

Twelve common orders physically replicate; eight releases reach the carrier.
The replica is disconnected and promoted. The old primary accepts 59 commands,
with an initial prefix captured and dispatched. The connector is paused during
recovery; the remaining old-branch commands and 59 new-branch commands are accepted.
Both branches reuse numeric outbox IDs. The old branch's WAL is archived, then a real
rewind replaces the old primary with the new timeline. The original CDC connector
is restarted against that rewound node. These operations, not injected log text or
private failure labels, produce the incident. There are 138 initial command receipts.

## Public information and business acceptance

Initial handover contains customer symptoms, the order/dispatch goal and a root
terminal in `/srv/commerce`. It does not name the databases, rewind, archive,
connector, Kafka, recovery method, dangerous operations or private grading state.
The agent can discover deployed code, configuration, normal logs, database tools,
backup metadata, WAL archives, Kafka administration tools and carrier documentation.
Nothing in this file or the artifact controls is installed in the agent image.

Customer requests continue every twelve real seconds during model inference and
commands. No action advances a synthetic business clock. Short maintenance is
allowed by the service contract; refused traffic remains reported. There is no
private-state verification action and no required self-check sequence.

After handover, two independent customer phases create, amend, release and cancel
orders, separated by a real restart. The carrier process reconnects to the new
network namespace with its same persisted volume; no snapshot is restored. All
accepted commands define the expected order state and shipment contents. The
evaluator checks every resulting order and the separate carrier ledger, including
missing, wrong, unexpected and duplicate bookings. Each phase allows the ordinary
sixty-second dispatch latency. Request retry and conflicting-ID behavior are also
checked. The observations never enter model feedback. Different valid architectures
and recovery methods are accepted on these same outcomes.

## Qualification and decision

Development runs already executed actual rewind and PITR. The first two full
recovery attempts passed before restart but missed four new dispatches after restart:
the consumer exhausted Supervisor's startup retries while Kafka was booting. Those
attempts remain under `artifacts/stream-dev-preserve-01` and `-02`. The image now
restarts the consumer across broker startup and provides working Kafka/Connect
logging. The third complete development recovery passed both business phases.
This is implementation qualification, not a model result or difficulty evidence.

The declared controls are untouched, restoration/table merging without receipt
migration, blind replay with new idempotency keys, and complete preservation and
reconciliation. They are known-solution artifact experiments, not blind reference
policies. The complete control recovers from ordinary backup/WAL, reconciles by
customer reference/revision and event UUID, consults existing carrier bookings,
then starts a fresh CDC stream. It reads no evaluator receipts or private seed.

Freeze the image/source and execute these controls, then immediately screen a full
Sol max attempt through native tools. A clean delivery rejects the high-difficulty
claim for this candidate. A task failure requires attribution to an actual decision
and fresh public-information counterfactual execution. Provider, startup, observer,
context-capacity and protocol failures do not prove cognitive difficulty. Retain
every attempted episode; do not change the scenario or budget during a collection.
