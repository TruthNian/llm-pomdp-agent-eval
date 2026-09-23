# External settlement development study

Status: both scheduled attempts ended and were retained; Sol delivered and the
GLM route timed out. Seven controls and both observed model trajectories matched
fresh execution. **The configuration-invariance check failed.** This is development
integration evidence, not a strictly controlled model comparison or a difficulty claim.

[Model trajectories](trajectories.html) · [Control trajectories](controls.html) ·
[Model evidence](model-evidence.json) · [Control evidence](control-evidence.json) ·
[Execution and file hashes](execution.json)

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

## Qualified mechanism controls

All seven completed under source `019a605c6d26667822117b18bda5e21f4f977939`.
Every action response matched fresh HTTP/database execution. These are controlled
policies, not independent production tasks or strong-model results.

| Public-history policy | Mechanism | Delivered | Actions | Local mismatched orders | External mismatched orders | Additional excess settled cents |
|---|---|---:|---:|---:|---:|---:|
| Competent operator | Full | yes | 29 | 0 | 0 | 0 |
| Local-books-only repair | Full | no | 27 | 0 | 2 | 1200 |
| New-key retry | Full | no | 32 | 2 | 2 | 651 |
| Arrival-order projection | Full | no | 29 | 4 | 0 | 0 |
| Same arrival-order policy | No notification delay | yes | 26 | 0 | 0 | 0 |
| Operator delayed 12 ticks | Full | no | 37 | 2 | 2 | 1200 |
| Same delayed operator | No initial cancellation deadline | yes | 41 | 0 | 0 | 0 |

The local-only failure directly demonstrates why accounting balance is insufficient.
The new-key policy cancels a detected historical retry before settlement, but its
probe retries still cause two real extra transfers totalling 651 cents. The
arrival-order policy has correct external transfers but corrupt local state;
removing notification delay rescues the same policy. Missing the cancellation
window creates 1200 cents of extra external liability beyond available treasury.
Removing only that initial deadline rescues the same delayed operator.

The positive policy is runbook-aware and not claimed optimal. Controls do not
measure execution latency: their record's default elapsed value is not a timing
measurement and the report labels it unmeasured. One policy's designed failure is
not evidence that a competent model must fail.

## Retained model attempts

Both attempts used source `019a605c6d26667822117b18bda5e21f4f977939`,
`external-settlement/1`, open feedback, max reasoning, 80 actions, 600 seconds per
request and 3600 seconds per episode. No episode was retried or replaced.

| Requested route | Observed result | Actions / requests | Elapsed seconds | Additional excess settled cents |
|---|---|---:|---:|---:|
| gpt-5.6-sol | Delivered; all six orders reconciled externally and locally | 26 / 26 | 333.762263 | 0 |
| custom/z-ai/glm-5.3 | Request 10 exceeded 600 seconds; incomplete delivery | 9 / 10 | 901.874207 | 0 |

Sol first read the operating contract, queried authoritative provider state,
canceled the duplicate at action 7, fixed retries/event ordering at action 10,
funded and resubmitted the failed refund at actions 13–14, then submitted two
probes and checked real completion. One SQL column-name error remained in the
trace; it recovered using feedback. The final verification passed, followed by
explicit handover. No pending provider operation or notification remained.

The GLM route initially used the wrong `action` field twice, then recovered.
Request 7 produced malformed completed action text and became an ordinary rejected
turn. It read the worker contract and retrieved authoritative state at action 9.
Request 10 timed out before another action was applied. Two orders remained
externally mismatched, one provider operation pending, two outbox items unresolved,
and no probes had been submitted. That is a retained incomplete attempt, not
proof of inability to reason about cancellation or refunds. The business clock
stopped at tick 9; no speculative later consequences were fabricated.

Sol reported usage for all 26 requests: 92,044 input and 8,521 output tokens,
including 7,899 reasoning tokens within output. The GLM route reported usage for
9 of 10 requests: those known requests total 11,157 input and 18,213 output tokens,
including 18,064 reasoning tokens. **The complete GLM token total is unknown.**
All 26 Sol response labels matched the requested name. All nine completed GLM
response labels differed; request 10 had no completed label. Names and usage are
provider reports, not independent weight or compute attestation.

## Configuration-invariance failure

The original launcher compared the bytes of three local configuration/auth files
before and after collection, storing only one combined Boolean. That value is
**false**, and is preserved unchanged in `model-evidence.json`. A later read-only
metadata check found `config.toml` last written at 2026-09-23 02:54:37 UTC, within
the collection interval; the then-current route URL still matched the frozen plan.
This does not identify the changed fields, the writer, or whether routing behavior
was affected. No baseline file contents or per-file comparison had been retained.
We cannot assert unchanged collection settings or invent a benign explanation.

Both databases and every service response still match fresh reconstruction of the
recorded actions. This establishes the business consequences of those actions;
it does not repair the configuration-control failure. The report prominently
separates this integration evidence from a controlled model comparison. Verification
checks that the failure is retained and disclosed, and prints FAILED for that
control; it does not convert it into a pass.

After collection, the launcher was improved to retain per-file equality Booleans
for future collections without saving configuration contents or credentials. This
new diagnostic file does not exist retroactively for this run. The old launcher
is available at the frozen source commit.

## Decision and next development gate

Retain this version as an **external-consequence anchor**, not a frontier-hardness
result. Its useful addition is that local repair, external completion and irreversible
loss now diverge measurably. The competent operator and Sol delivered; the second
route ended at the transport layer, so this collection does not establish business
reasoning discrimination between the routes.

The next difficulty work must address the fixed repair recipe. In this task, a
small documented settings patch plus an all-orders provider retrieval exposes most
of the remaining decision. More orders, smaller deadlines, extra JSON failures or
another renamed payment scenario would not solve that limitation. Prioritize a
complete cross-component incident whose faulty transformation/identity rule must
be located and repaired from evidence, with multiple independently constructed
fault mechanisms and useful query/test tools retained. A single fixed configuration
patch must fail to repair the whole candidate set. Each mechanism needs its own
public-history feasibility control before another frozen model calibration.

This is the selected next development gate, **not implemented by this study**.
Actual external-task predictive validity and sustained frontier difficulty remain
unachieved. No model ranking, population success rate or parameter/training claim
is supported by this one constructed scenario.
