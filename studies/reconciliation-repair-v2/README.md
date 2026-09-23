# Reconciliation network-recovery follow-up

**Both new Sol max attempts delivered in 28 actions. These contracts did not establish frontier difficulty.**

This is a separately frozen follow-up after the user reported a network outage.
The two original failures in [v1](../reconciliation-repair-v1/README.md) remain
unchanged. They are not replaced, renamed or silently pooled with these attempts.
The business contracts, tool interfaces, 80-action budget, 600-second request budget,
3600-second episode budget and max route match v1. Source was frozen at `f3db4ee3778c18decf87c944c16e3d2e00c97491`.

| Contract | Outcome | Actions | Seconds | Input / output tokens |
|---|---|---:|---:|---:|
| Capture snapshots | Delivered | 28 | 258.616 | 87,806 / 6,287 |
| Posting corrections | Delivered | 28 | 300.231 | 98,886 / 7,705 |

No invalid actions or adapter errors occurred. All 56 completed request labels
matched the requested route; returned labels do not certify model weights.
All 56 requests included token usage. Config, auth and consent bytes were unchanged.
Every action response and final database matched fresh execution of the frozen
2.11 package. Fresh execution validates the record, not a second independent model run.
There is no GLM result or model ranking in this follow-up.

Decision: retain as executable source-repair regression anchors. Do not keep
calling these high-difficulty candidates or add more rows to claim headroom.

- [Complete readable trajectories](trajectories.html)
- [Complete sanitized evidence](model-evidence.json)
- [Frozen plan](plan.json) and [byte bindings](execution.json)

```bash
python tools/service_study.py verify studies/reconciliation-repair-v2
```

The command regrades recorded behavior; it does not call a provider or run candidate SQL.
