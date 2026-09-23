"""Contract-aware feasibility controls. No case, seed, audit, or future feed access.

The SQL is a hand-written implementation of the public contracts, not a general
source-repair solver. Success demonstrates feasibility, not model difficulty.
"""

RESOLVE = "SELECT merchant,object,currency,amount_minor FROM (SELECT *,row_number() OVER (PARTITION BY merchant,object ORDER BY epoch DESC,revision DESC,receipt DESC) AS n FROM normalized) WHERE n=1"
AGGREGATE = "SELECT merchant,currency,sum(amount_minor) AS net_minor FROM positions GROUP BY merchant,currency"


def correction(contract):
    if "FULL CAPTURE SNAPSHOTS" in contract:
        normalize = """SELECT receipt,json_extract(body,'$.merchant') AS merchant,
json_extract(body,'$.capture_id') AS object,json_extract(body,'$.currency') AS currency,
json_extract(body,'$.generation') AS epoch,json_extract(body,'$.revision') AS revision,
CASE json_extract(body,'$.schema') WHEN 1 THEN
minor(json_extract(body,'$.captured'),json_extract(body,'$.currency'),'minor')-
minor(json_extract(body,'$.refunded'),json_extract(body,'$.currency'),'minor')
WHEN 2 THEN minor(json_extract(body,'$.money.captured'),json_extract(body,'$.currency'),'major')-
minor(json_extract(body,'$.money.refunded'),json_extract(body,'$.currency'),'major') END AS amount_minor
FROM receipts"""
    elif "CORRECTABLE POSTINGS" in contract:
        normalize = """SELECT receipt,json_extract(body,'$.account') AS merchant,
json_extract(body,'$.entry_id') AS object,json_extract(body,'$.currency') AS currency,
0 AS epoch,json_extract(body,'$.revision') AS revision,
CASE WHEN json_extract(body,'$.status')='posted' THEN
CASE json_extract(body,'$.kind') WHEN 'refund' THEN -1 ELSE 1 END *
minor(json_extract(body,'$.amount'),json_extract(body,'$.currency'),json_extract(body,'$.unit'))
ELSE 0 END AS amount_minor FROM receipts"""
    else:
        raise ValueError("No known public contract in observed history")
    return {"normalize": normalize, "resolve": RESOLVE, "aggregate": AGGREGATE}


def policy_action(request, variant="complete"):
    history = request["history"]
    seen = [entry["action"] for entry in history]
    for doc in ("operations", "contract", "schema", "pipeline", "source", "timing"):
        action = {"command": "inspect", "target": doc}
        if action not in seen:
            return action
    contract = next(e["observation"]["result"]["text"] for e in history if e["action"] == {"command": "inspect", "target": "contract"})
    sources = correction(contract)
    if not any(a["command"] == "query" for a in seen):
        return {"command": "query", "target": "SELECT receipt,body FROM receipts ORDER BY receipt"}
    if not any(a["command"] == "provider" for a in seen):
        return {"command": "provider", "target": "all"}
    if variant == "normalize_only":
        sources = {"normalize": sources["normalize"]}
    elif variant == "fixed_resolver":
        sources = {"resolve": RESOLVE}
    elif variant == "no_epoch":
        sources["resolve"] = RESOLVE.replace("epoch DESC,", "")
    elif variant == "global_identity":
        sources["resolve"] = RESOLVE.replace("PARTITION BY merchant,object", "PARTITION BY object")
    elif variant == "positive_only":
        sources["aggregate"] = AGGREGATE.replace("GROUP BY", "WHERE amount_minor>0 GROUP BY")
    elif variant not in ("complete", "no_refresh"):
        raise ValueError("Unknown control variant")
    for stage, sql in sources.items():
        if not any(a["command"] == "patch" and a["target"]["stage"] == stage for a in seen):
            return {"command": "patch", "target": {"stage": stage, "sql": sql}}
    for command in ("test", "deploy"):
        if not any(a["command"] == command for a in seen):
            return {"command": command}
    if sum(a["command"] == "workload" for a in seen) < 2:
        return {"command": "workload", "target": 1}
    last = history[-1]
    if last["action"]["command"] == "verify":
        return {"command": "finish"}
    if last["action"]["command"] == "refresh":
        return {"command": "verify"}
    if last["action"] == {"command": "inspect", "target": "metrics"}:
        if last["observation"]["result"]["pending_receipts"]:
            return {"command": "wait"}
        return {"command": "verify" if variant == "no_refresh" else "refresh"}
    return {"command": "inspect", "target": "metrics"}
