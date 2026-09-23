# External settlement development study

Status: protocol to be frozen before model requests; collection results will be
published with all failures. One constructed scenario, not a model ranking.

The [environment contract](../../docs/EXTERNAL_SETTLEMENT.md) defines independent
provider/local state, irreversible transfers, finite refund liquidity, delayed
notifications, cancellation and explicit final verification. Old incident records
are unchanged. No real provider accounts or funds are involved.

`plan.json` fixes one complete episode for each existing Sol/GLM route at max,
80 actions, 600-second request deadlines and 3600-second episode deadlines.
Both get the same public contract and all feedback. Missing provider usage remains
unknown; requested model names are routes, not proof of the underlying weights.
No failed episode may be replaced. Format/transport failures do not prove difficulty.

`controls.py` executes seven public-history controls: the competent operator,
local-books-only repair, new-key retry, arrival-order reconciliation with/without
notification delay, and a delayed operator with/without the initial cancellation
deadline. The realized sequences are stored as action artifacts; the policy source
shows how each was derived using public observations. Control separation is a
mechanism check, not strong-model calibration or an optimality claim.

```powershell
python studies/external-settlement-v1/controls.py artifacts/external-controls.json
python -m pomdp_bench prepare-settlement-suite --out artifacts/external-suite.json
```

`launcher.py` uses the already configured local authenticated route without
changing settings. `export.py` reconstructs both databases by reexecuting each
recorded action against fresh services; it requires the frozen collection source.
Shared `validate`/`recheck` commands also support this task family.
