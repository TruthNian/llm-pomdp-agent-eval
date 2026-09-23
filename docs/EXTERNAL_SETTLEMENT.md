# External settlement with delayed evidence

Status: implemented as `external-settlement/1` in framework 2.10.0.
The earlier incident remains a workflow anchor. The [frozen development study](../studies/external-settlement-v1/README.md) separates mechanism qualification from strong-model calibration.

## Why this mechanism

The current local `adjust` action can immediately correct the same ledger that
acceptance reads. That is useful for bookkeeping recovery but removes an important
real integration problem: an internal correction need not complete an external
operation. Add that missing dependency before adding more services or task volume.

Relevant operational constraints are documented by a real provider:

- Refunds can remain pending when available funds are insufficient. Cancellation
  depends on the payment/refund state; a succeeded PaymentIntent cannot simply
  be canceled. These are distinct from editing a merchant's internal ledger.
  [Stripe refund/cancellation documentation](https://docs.stripe.com/refunds).
- Event delivery can be duplicated and out of order; the arrival order is not an
  authoritative operation history. The current object can be retrieved separately.
  [Stripe webhook delivery behavior](https://docs.stripe.com/webhooks#event-ordering).
- An API error can leave the operation's outcome indeterminate. Retrying with a
  new identity can cause another side effect; same-key network retries and
  reconciliation of server errors are different cases.
  [Stripe error handling](https://docs.stripe.com/error-low-level).

Sources checked 2026-09-20. They motivate the mechanism, not a claim that the
benchmark reproduces Stripe or a particular production incident. No real provider
account, live money or customer data is required.

## Implementation requirements

Keep the shared collector and bounded operator interface. Add a separate trusted
provider ledger and an event-delivery queue. Local entries, received events and
authoritative provider state must be distinct persisted data. The public contract
must explain which reads are authoritative and that effects/notifications can lag.

Use a disclosed finite cancellation window and settlement schedule in business
ticks. Before settlement, an eligible pending operation can be canceled. After
settlement, recovery requires a separate external compensating operation that can
itself be pending or fail. Never let a local accounting write undo provider history.
These are constructed transition rules; do not label tick counts as banking times.

The agent must stop future duplicate work, reconcile uncertain existing operations,
choose cancellation or compensation from evidence and deliver only after the
external result is terminal. Verification reads/checks the resulting business state;
it must not secretly complete pending operations on the agent's behalf.

## Acceptance of this development step

First demonstrate an observation-only operator completing the task, and concrete
failures for local-balance-only repair, blind new-key replay and last-event-wins
reconciliation. Make the same competent policy observe different consequences when
delay or the cancellation window is removed; otherwise the new mechanism adds no
decision requirement and should be deleted.

Then freeze the scenario, public contract, tools and budgets before complete
strong-model runs. Keep arithmetic/query tools available. Success/failure,
unresolved external obligations and irreversible extra transfers are the outputs;
JSON mistakes and transport failures do not establish cognitive difficulty.
If competent scripts and both strong model configurations still solve it readily,
retain the anchor and identify the next missing decision instead of calling it hard.

## Concrete state and actions

`local.sqlite` contains orders, outbox, received events, projection, last retrieved
provider snapshots, adjustments and active configuration. Its `books` view sums
succeeded projected operations plus local adjustments. `provider.sqlite` separately
persists operation objects, notifications, immutable transfers and a wallet. Local
SQL cannot read that database. The `provider` command performs an HTTP retrieval
and updates snapshots only; `cancel`, `refund` and `fund` perform independent HTTP
operations. A failed item in a batch does not roll back successful external items.

The initial four obligations have different evidence histories: one pending
extra charge, one already settled extra charge with a pending refund, one request
that never arrived and one request whose committed acknowledgement was lost.
The paused retry worker starts with attempt-based keys and arrival-order event
projection. Correctness is determined from resulting rows, not configuration flags.

The public alert identifies the initial tick-12 boundary. Each normal action acts
first, then advances one business tick, even when invalid. New charges/refunds
settle four ticks after creation. Notifications arrive within eight ticks, possibly
out of order and duplicated. Valid `verify` and `finish` spend an action but leave
business state/time unchanged. `wait` advances one tick. Nothing settles merely
because the agent asked for verification. Each episode allows 80 actions.

There are 800 cents of treasury and initially no refund reserve. Refunds fail
terminally when insufficiently funded at settlement; repeating the same key still
returns that failed object. The existing settled extra charge requires all 800
cents. Allowing the pending duplicate to settle introduces another 1,200 cents of
external liability; local edits cannot restore the missing liquidity. These are
constructed operational units and do not model banking times or real balances.

At least two explicit workload probes must be accepted and correctly settled.
Each probe loses its first acknowledgement after commit, so new-key retry really
creates another operation. Historical recovery alone cannot satisfy handover.
Success requires exact external net transfers and exact local books for all orders,
no pending operations/outbox/notifications, enabled processing, and a current PASS
followed by explicit finish. The grader does not require a named configuration or
a prescribed action sequence. Extra gross settled debits remain in immutable
transfer history even after compensation; they are reported separately from success.

## Counterfactuals and measurement limits

`immediate_events` removes notification delay (settlement still takes four ticks).
`no_cancel_deadline` removes automatic settlement of the initial pending duplicate
only; other operations retain their timing. These are explicit mechanism ablations,
not extra independent task samples. Both cluster with the same source scenario.
The same public-history arrival-order policy and delayed operator are each compared
with/without their relevant constraint. SQL and arithmetic are never withheld.

External excess and pending-operation exposure accumulate once per actual business
tick; repeated read-only verification/handover does not inflate them. Provider
state hashes cover both databases. Recorded replay starts no services; fresh
reproduction executes every HTTP/database action and compares all responses.

This version adds real consequences to a constructed task. It does not establish
production predictive validity, high model-discrimination power, contamination
resistance or a calibrated difficulty ladder. Those require separate evidence.
