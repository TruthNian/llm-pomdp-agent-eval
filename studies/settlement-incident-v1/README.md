# Complete settlement incident trajectories

The [service contract](../../docs/SERVICE_INCIDENT.md) restores the complete
investigation/action/feedback/recovery loop missing from the localized patch screen.
It operates actual HTTP and SQLite state in a constructed local business system.

The six controls are a runbook-aware public-observation operator, healthy-process
handover, staged configuration without restart, repair of future processing only,
blind rollback, and investigation until the deadline. Only the complete operator
should deliver. Every trajectory is re-executed against fresh services and data.

[The model plan](plan.json) fixes one full open episode for each user-authorized
Sol and GLM route at max reasoning, 60 action ticks, 3600 wall seconds and a
600-second per-request deadline. Models receive every public result and can
correct errors inside the same episode. Episodes are never replaced by retries.
Prepared source and request settings are fixed before collection.

## Observed outcomes

[Read both complete recorded timelines](trajectories.html), including the initial
public contract, every action/result, private evaluator audit and reconstructed
final database. Download the HTML and open it locally if GitHub shows source.
[Model records](model-evidence.json) and [all six controls](control-evidence.json)
were collected from clean source `9fcfb8299ee8ba8cbcd7fff701daef8aa451a97b`.

| Requested route, max reasoning | Terminal outcome | Applied actions / requests | Mismatched orders / unsettled messages | Excess-debit cent·ticks |
|---|---|---:|---:|---:|
| gpt-5.6-sol | Accepted, verify then finish | 20 / 20 | 0 / 0 | 26,973 |
| custom/z-ai/glm-5.3 | Parser/adapter termination | 13 / 14 | 10 / 6 | 37,191 |

Sol read operational documents and configuration, rolled back the worker, then
staged compatibility/order-idempotency settings and restarted. During rollback,
new v2 messages became dead letters. It queried the joined business records,
adjusted two existing excess debits, replayed messages, rebuilt the malformed
payload and corrected another duplicate exposed by replay. A final verification
submitted four new orders; all 29 accepted orders reconciled before handover.
This is an observed recovery path, not proof that rollback was optimal.

GLM first used `action` instead of `command`, received an error, corrected it,
read the runbooks, configured/restarted the worker and queried the six dead
messages. Request 14 then failed the old parser with
`Endpoint did not return one unambiguous JSON action`. The old error conflates
action syntax and envelope shape. Raw response bodies were not retained, so we
cannot diagnose its exact cause retrospectively. This is **not a demonstrated
reasoning failure**. All 14 requests' reported usage remains counted, even though
only 13 environment actions ran. The first 13 reported model labels differed
from the requested GLM route; the rejected response's label was not recorded by
that adapter. Neither matching nor mismatching labels attest actual model weights.

Reported input/output tokens were 50,492 / 8,260 for Sol and 19,981 / 25,165 for
GLM; elapsed episode times were 224.58 and 420.10 seconds. These are provider
usage and measured wall time, not compute-matched or price estimates. Both budgets
were fixed before collection; the failed attempt was not restarted or replaced.

Exposure sums include the initial incident's excess debits and stop at each
attempt's termination. Different stopping times prevent a direct efficiency
ranking; a failed early handover may have a small sum while leaving unpaid orders.
See the [exact measurement definitions](../../docs/SERVICE_INCIDENT.md).

Only the runbook-aware operator delivered among the six controls. Process health,
configuration without restart, future-only repair and rollback left actual
accounting/backlog failures; repeated inspection exhausted the action horizon.
Every original action in all eight episodes matched a fresh HTTP/SQLite execution.
The published final tables are those independent reconstructions, whose hashes
match the original final state; they are not falsely labeled original DB files.

## Decision and verification

This is one development scenario cluster. Sol's successful complete trajectory
establishes a usable workflow anchor, **not the required frontier difficulty**.
GLM's parser termination cannot establish separation. The missing delivery loop
has been restored, but the high-difficulty benchmark objective remains unfinished.

The next concrete environment mechanism is delayed, irreversible external
settlement: local ledger balance alone must not imply a completed customer refund.
Its public contract must expose the possibility and available reconciliation tools;
future evidence timing and action ordering should determine whether a repair is
still possible. Preserve this simpler scenario as a regression anchor.

Separately, framework 2.9.1 lets completed malformed action text consume a rejected
turn with feedback. Envelope/transport failures still terminate. Its single
[additional GLM integration plan](../settlement-incident-v2/plan.json) is a new
attempt, not a replacement for the failure here. Do not pool versions or rank models.

```bash
python studies/settlement-incident-v1/verify.py
```

This regrades the published records, checks file identities and the HTML against
the records without executing services or calling models. Reproduce original
service execution with the source commit recorded in [execution.json](execution.json).
