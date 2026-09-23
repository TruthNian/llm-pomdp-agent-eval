"""Known-contract public-history feasibility controls, not a general repair agent."""
DECODE = "SELECT receipt,json_extract(body,'$.operation_id') AS operation_id,json_extract(body,'$.order_id') AS order_id,json_extract(body,'$.amount_cents') AS amount_cents,json_extract(body,'$.status') AS status,json_extract(body,'$.version') AS version FROM receipts WHERE event_type IN ('refund.created','refund.updated')"
PROJECT = "SELECT operation_id,order_id,amount_cents,status,version FROM (SELECT *,row_number() OVER (PARTITION BY operation_id ORDER BY version DESC,receipt DESC) AS n FROM decoded) WHERE n=1"
DISPATCH = "SELECT intent_id,order_id,charge_id,amount_cents,request_key AS key FROM queue"


def policy_action(request, variant="complete"):
    history = request["history"]
    seen = [e["action"] for e in history]
    for doc in ("operations", "contract", "events", "schema", "pipeline", "timing", "source"):
        action = {"command": "inspect", "target": doc}
        if action not in seen:
            return action
    sources = {"decode": DECODE, "project": PROJECT, "dispatch": DISPATCH}
    if variant == "new_keys":
        sources["dispatch"] = DISPATCH.replace("request_key AS key", "request_key || '/attempt-' || attempt AS key")
    elif variant == "updated_only":
        sources["decode"] = DECODE.replace("IN ('refund.created','refund.updated')", "='refund.updated'")
    elif variant == "charge_amount":
        sources["decode"] = DECODE.replace("$.amount_cents", "$.charge_cents")
    elif variant == "order_identity":
        sources["project"] = PROJECT.replace("PARTITION BY operation_id", "PARTITION BY order_id")
    elif variant == "swapped_allocations":
        sources["dispatch"] = "SELECT intent_id,order_id,charge_id,CASE WHEN order_id NOT IN ('order-a','order-b','order-c') THEN (SELECT sum(q.amount_cents) FROM queue q WHERE q.order_id=i.order_id)-amount_cents ELSE amount_cents END AS amount_cents,request_key AS key FROM queue i"
    elif variant not in ("complete", "same_failed_key", "no_refresh"):
        raise ValueError("Unknown refund control")
    for stage, sql in sources.items():
        if not any(a.get("command") == "patch" and a["target"]["stage"] == stage for a in seen):
            return {"command": "patch", "target": {"stage": stage, "sql": sql}}
    for command in ("test", "deploy"):
        if not any(a.get("command") == command for a in seen):
            return {"command": command}
    last = history[-1]
    command, result = last["action"]["command"], last["observation"]["result"]
    if command == "verify":
        return {"command": "finish"}
    if command == "refresh":
        return {"command": "verify"}
    if last["action"] == {"command": "inspect", "target": "metrics"}:
        if result["undelivered_events"]:
            return {"command": "wait"}
        return {"command": "verify" if variant == "no_refresh" else "refresh"}
    if command == "query":
        return {"command": "provider", "target": "all"}
    if command != "provider":
        return {"command": "query", "target": "SELECT intent_id,request_key FROM refund_intents ORDER BY intent_id"}
    intents = next(e["observation"]["result"]["rows"] for e in reversed(history) if e["action"]["command"] == "query")
    by_key = {row[1]: row[0] for row in intents}
    if variant != "same_failed_key":
        for obj in result["operations"]:
            if obj["kind"] == "refund" and obj["status"] == "failed" and obj["key"] in by_key:
                return {"command": "retry", "target": {"intent_id": by_key[obj["key"]], "key": obj["key"]+"/recovery"}}
    if result["wallet"]["treasury_cents"]:
        return {"command": "fund", "target": result["wallet"]["treasury_cents"]}
    if not any(a == {"command": "configure", "target": {"enabled": True}} for a in seen):
        return {"command": "configure", "target": {"enabled": True}}
    if sum(a.get("command") == "workload" for a in seen) < 2:
        return {"command": "workload", "target": 1}
    if any(o["status"] == "pending" for o in result["operations"]):
        return {"command": "wait"}
    return {"command": "inspect", "target": "metrics"}
