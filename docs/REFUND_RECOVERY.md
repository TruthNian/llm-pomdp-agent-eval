# Refund recovery: external-settlement/2

Framework 2.12 couples editable callback and dispatch SQL to the existing external
payment environment. It is one constructed compound scenario, not a production
incident reproduction or execution of the upstream applications below.

## Business outcome and information

Deliver each approved partial refund exactly, reconcile local books, repair the
deployment and exercise two fresh batches. Multiple refund intents share a charge.
The worker starts paused after HTTP failures with uncertain commitment. Public
SQL, executable source, staged intermediate output and authoritative provider reads
remain available. There is no cancel-before-inspection deadline.

Three actual SQL components decode callbacks, select current refund objects and
dispatch ready intents. The provider runs through HTTP with its own SQLite database.
Settled transfers are immutable; local adjustments cannot refund or recharge a
customer. Finite reserve couples recovery decisions across obligations.

Each normal action advances worker, settlement and callback delivery once. Even
test/deploy actions allow an enabled worker to run at the following tick. Pause it
to test without outbound work. Test executes SQL without sending requests itself;
deploy does not backfill. Refresh rebuilds the projection. Verify/finish do not
advance anything. Other actions expire PASS; explicit finish is necessary.

The grader checks external money **per intent and per order**, each provider refund's
operation/order/amount/status/version in the local projection, empty backlog,
received callbacks, enabled processing and a current materialization. Correct total
money cannot hide swapped partial refunds or offsetting wrong projection rows.
Each request key has a single intent owner, retained across retries. Acceptance
uses provider operations and transfer history, never reference SQL text.

## Source grounding and limits

- [Hi.Events issue 1067](https://github.com/HiEventsDev/Hi.Events/issues/1067)
  reports pending refund records caused by missing callback types.
  [Merged PR 1156](https://github.com/HiEventsDev/Hi.Events/pull/1156)
  adds `refund.created` and `charge.refunded` handling (merged 2026-04-18;
  merge `081c1a0de173ce54e35d100af2f88da9056234ca`). The changed handler was
  inspected. Its reported test-mode check is not a production validation claim.
- [OpenCode issue 28398](https://github.com/anomalyco/opencode/issues/28398)
  reports duplicate callback deductions and original-payment amounts used for
  partial refunds. The inspected [immutable webhook source](https://github.com/anomalyco/opencode/blob/45719acebbd54afb29103d4d842e3cae67578010/packages/console/app/src/routes/stripe/webhook.ts)
  deducts `payment.amount` in the top-up `charge.refunded` branch without checking
  `timeRefunded` there. The issue closed through inactivity; this is not a
  maintainer-confirmed remediation or reproduced end-to-end production exploit.
- [Stripe refund documentation](https://docs.stripe.com/refunds) distinguishes
  partial refund amounts, refund lifecycle events and charge summaries.
  [Webhook documentation](https://docs.stripe.com/webhooks) describes duplicate
  delivery and lack of event-order guarantees.

Our simplified payloads, initial amounts, finite treasury, lost acknowledgements,
four-tick terminal refund failure and eight-tick notification bound are constructed
fixtures. They are not taken from those incidents. In particular Stripe card
refunds may remain pending for insufficient balance: this environment's terminal
failure rule is a generic provider contract, not an exact Stripe implementation.
No upstream code is copied or executed. Two source reports do not make two task
clusters. No contamination-resistance or predictive-validity claim is established.

## Run and reject weak difficulty claims

```bash
python -m pomdp_bench prepare-refund-suite --out artifacts/refund-suite.json
python -m pomdp_bench run --suite artifacts/refund-suite.json --agents examples/refund-agents.json --out artifacts/refund-run
python -m pomdp_bench validate artifacts/refund-run
```

The hand-written public-history reference establishes feasibility. Seven damaged
variants isolate new retry keys, missing created callbacks, charge/refund amounts,
order/refund identity, reuse of a terminal failed key, missing refresh and swapped
allocations. These are mechanism controls, not model difficulty evidence.

The [frozen screen](../studies/refund-recovery-v1/plan.json) gives Sol max 100 actions,
600 seconds/request and 3600 seconds overall. A clean success rejects this candidate
as high-difficulty evidence. A cognitive failure would justify investigation, not
automatically establish durable difficulty. If solved, stop extending this family
of miniature SQL fixtures as the frontier mainline; keep it as regression evidence.

The [completed screen](../studies/refund-recovery-v1/README.md) delivered in 39/100
actions with no excess refund, invalid action or adapter error. This candidate
failed the high-difficulty objective. It is retained as regression evidence; further
miniature SQL fixture expansion is no longer the frontier mainline.
