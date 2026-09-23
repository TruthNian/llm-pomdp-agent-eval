# Recovery-completeness counterfactual

Both post-hoc artifact experiments completed. This is not a new model attempt
or a claim that a model would change its policy after a hint.

The [frozen plan](plan.json) copies all twenty-eight executed Bash actions from the
completed Sol attempt. Both arms preload its twenty-two accepted customer batches
from before maintenance, disable further background requests, and wait sixty seconds
before its snapshot and dispatch-completeness gates (actions 23 and 26). These changes
make the model's fixed count assertions executable without pretending to reproduce
thirty-two minutes of inference timing. Terminal customer workloads and restart
acceptance remain the same. Every original command, including failed ones, is retained.

The intervention arm then restores the ordinary physical backup/WAL and merges
missing data before handover. It does not replace the model's repaired consumer,
CDC configuration or existing carrier receipts. The original arm receives no such
recovery. Both use the same immutable image and business grader.

The predicted result is that the original artifact still misses twelve orders and
nine dispatches, while data restoration resolves them. Any exit-code mismatch,
failed prediction or observation error must remain visible. Even a successful
contrast identifies a data-completeness mechanism in this constructed incident;
it does not isolate the effect of the stateless model adapter or establish population
difficulty. A separately frozen continuous-session screen is still required.

## Observed outcome

| Matched artifact arm | Accepted orders / releases after restart | Missing order states | Missing dispatches | Delivered |
|---|---|---:|---:|---|
| Original model commands | 94 / 76 | 12 | 9 | No |
| Same commands, then data-only recovery | 94 / 76 | 0 | 0 | Yes |

Both arms had zero command exit-code mismatches relative to the original commands,
zero observer/retry errors, and zero duplicate, unexpected or changed bookings.
The intervention preserved the model's event-UUID receipt migration, repaired
consumer and fresh CDC configuration. It recovered historical data through ordinary
backup/WAL before the same terminal business workloads and real restart.

This supports incomplete historical recovery as the direct business failure mechanism.
It does not prove whether the model's omission was caused by reasoning ability, its
stateless adapter, or their interaction. The continuous-session screen addresses
that measurement limitation separately.

Retained evidence: [original arm](original.json), [data recovery arm](restore_missing.json).
Run `python studies/stream-recovery-counterfactual-v1/verify.py` to regrade and verify
the exact copied commands, intervention, matched workload and source/image bindings.
