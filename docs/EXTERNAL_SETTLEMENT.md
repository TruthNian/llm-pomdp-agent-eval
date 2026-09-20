# Next scenario: external settlement with delayed evidence

Status: selected next implementation, **not yet implemented or calibrated**.
The current settlement incident remains an executable workflow anchor.

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

## Smallest useful implementation

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
