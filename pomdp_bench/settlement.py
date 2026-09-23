"""External-settlement task and public-history operator control."""
from .incident import IncidentEnvironment
from .settlement_runtime import Runtime

VERSION = "external-settlement/1"
POLICY = "settlement_operator"
PROFILES = ("delayed", "immediate_events", "no_cancel_deadline")


def make_case(profile="delayed"):
    if profile not in PROFILES:
        raise ValueError("Unknown external settlement profile")
    return {"generator_version": VERSION, "family": "external_settlement", "profile": profile,
            "domain": "payment_operations", "source_task_id": "constructed/external-settlement-v1", "max_steps": 80}


def suite():
    return {"generator_version": VERSION, "cases": [make_case()]}


def validate_case(case):
    if case != make_case(case.get("profile")):
        raise ValueError("Unknown external settlement contract")


def healthy(audit):
    return (not audit["book_mismatches"] and not audit["external_mismatches"]
            and not audit["pending_operations"] and not audit["unsettled_messages"]
            and not audit["undelivered_events"] and audit["worker_enabled"] and audit["probe_orders"] >= 2)


class SettlementEnvironment(IncidentEnvironment):
    validate_case = staticmethod(validate_case)
    healthy = staticmethod(healthy)

    def __init__(self, case, condition="open", *, recorded_calls=None):
        super().__init__(case, condition, recorded_calls=recorded_calls)
        self.last_result = {"alert": "Take over settlement recovery. The retry worker is paused. HTTP errors left uncertain external payments, a duplicate refund is unresolved, and events may disagree with actual state. A pending charge reaches settlement at business tick 12; inspect provider state promptly.", "current_tick": 0}
        if case["profile"] == "no_cancel_deadline":
            self.last_result["alert"] = self.last_result["alert"].replace("A pending charge reaches settlement at business tick 12", "In this cancellation-deadline ablation, the initial duplicate charge remains cancelable indefinitely")

    def make_runtime(self):
        return Runtime(self.case)

    def contract(self):
        return {"family": "external_settlement", "task": "Deliver correct payment settlement for every accepted order, historical and new. Stop duplicate external transfers, resolve pending/failed recovery, reconcile local books, and hand over with the retry worker enabled. Available refund treasury is finite; settled charges cannot be canceled. You control investigation, containment, recovery, testing and verification.",
                "workspace": "Trusted local HTTP provider plus separate file-backed provider/local SQLite databases. No real money, accounts, or model source execution.",
                "actions": {
                    "inspect": "target: operations, provider-contract, schema, worker, timing, config, metrics",
                    "query": "target: read-only LOCAL SQLite query; joins/aggregation supported, 100 rows; inspect schema",
                    "provider": "target: all OR 1..32 order_id strings; authoritative current HTTP read, stored in local snapshots; does not repair books",
                    "configure": "target: patch with enabled(bool), retry_identity(stable|attempt), event_order(version|arrival); immediate activation",
                    "cancel": "target: 1..32 operation_id strings; pending charges only, independent per-item results",
                    "fund": "target: positive integer cents; moves finite treasury to refund reserve",
                    "refund": "target: 1..32 {charge_id,amount_cents,key}; retrieve charge first, inspect provider-contract",
                    "adjust": "target: {order_id,delta_cents,key}; ONLY local books, no external transfer",
                    "workload": "target: integer 1..4; submit new probe orders; maximum 16 probes, at least two required",
                    "wait": "no target; one normal business tick",
                    "verify": "no target; READ-ONLY checks. No new traffic, settlement, draining, or repair",
                    "finish": "no target; explicit final handover; no work performed"},
                "limits": "80 actions including finish. Normal actions, including reads/rejections, act first then advance one tick. Valid verify/finish spend an action but freeze state. Every other action expires verification. Read timing and provider-contract for deadlines and delayed results. No wall-clock-dependent business state.",
                "mechanism": ("Notifications have zero delivery delay in this evidence ablation." if self.case["profile"] == "immediate_events" else
                              "The initial duplicate charge has no settlement deadline in this cancellation ablation; other operations retain ordinary settlement timing." if self.case["profile"] == "no_cancel_deadline" else
                              "Delayed, duplicated, out-of-order notifications; finite pending-charge cancellation window."),
                "success": "External net transfers AND local books equal each accepted order exactly. No pending provider operation, undelivered outbox item or outstanding notification. Worker enabled and at least two probe orders delivered correctly. verify PASS at the current state followed by finish. Permanent additional gross excess transfers are reported even if later refunded."}

    def grade(self):
        current = self.last_response
        audit = current["audit"] if current else None
        verified = bool(current and self.verified_state == current["state_sha256"])
        advanced = [c for i, c in enumerate(self.calls) if c["response"]["tick"] > (self.calls[i - 1]["response"]["tick"] if i else 0)]
        return {"success": bool(self.done and self.reason == "finished" and audit and healthy(audit) and verified),
                "termination": self.reason, "cost": len(self.history), "steps": len(self.history), "budget": self.case["max_steps"],
                "verified_current_state": verified, "invalid_actions": self.invalid_actions,
                "book_mismatches": len(audit["book_mismatches"]) if audit else None,
                "external_mismatches": len(audit["external_mismatches"]) if audit else None,
                **{k: audit[k] if audit else None for k in ("pending_operations", "unsettled_messages", "undelivered_events", "additional_excess_settled_cents", "worker_enabled", "probe_orders", "order_count")},
                "external_excess_cent_ticks": sum(sum(max(0, m["external_cents"] - m["amount_cents"]) for m in c["response"]["audit"]["external_mismatches"]) for c in advanced),
                "pending_operation_ticks": sum(c["response"]["audit"]["pending_operations"] for c in advanced),
                "http_requests": current["http_requests"] if current else 0}

    def evidence(self):
        evidence = super().evidence()
        evidence["runtime"] = "separate-provider-http-sqlite/1"
        return evidence


def policy_action(request, *, event_order="version", retry_identity="stable"):
    """Runbook-aware feasible policy, using public history only; no hidden IDs.

    Parameters are mechanism controls, not model assistance. The policy is not
    claimed optimal or general-purpose, and does not read grader results except
    the ordinary public verify response.
    """
    history = request["history"]
    seen = [e["action"] for e in history]
    for doc in ("operations", "schema", "provider-contract", "worker", "timing"):
        if {"command": "inspect", "target": doc} not in seen:
            return {"command": "inspect", "target": doc}
    configs = [a["target"] for a in seen if a.get("command") == "configure"]
    if not configs:
        return {"command": "configure", "target": {"enabled": False, "retry_identity": retry_identity, "event_order": event_order}}
    last = history[-1]
    command, result = last["action"]["command"], last["observation"]["result"]
    if command == "verify":
        return {"command": "finish"}
    if command == "inspect" and last["action"].get("target") == "metrics":
        return {"command": "wait"} if result["undelivered_events"] else {"command": "verify"}
    if command != "provider":
        return {"command": "provider", "target": "all"}
    operations = result["operations"]
    # Source amounts are learned from ordinary local SQL, not scenario constants.
    queries = [e for e in history if e["action"] == {"command": "query", "target": "SELECT order_id,amount_cents FROM orders ORDER BY order_id"}]
    if not queries:
        return {"command": "query", "target": "SELECT order_id,amount_cents FROM orders ORDER BY order_id"}
    expected = dict(queries[-1]["observation"]["result"]["rows"])
    cancel, refunds = [], []
    need = 0
    for oid, amount in expected.items():
        group = [o for o in operations if o["order_id"] == oid]
        charges = [o for o in group if o["kind"] == "charge" and o["status"] in ("pending", "succeeded")]
        credits = [o for o in group if o["kind"] == "refund" and o["status"] in ("pending", "succeeded")]
        excess = sum(o["amount_cents"] for o in charges) - sum(o["amount_cents"] for o in credits) - amount
        for obj in sorted(charges, key=lambda o: o["created_tick"], reverse=True):
            if obj["status"] == "pending" and excess >= obj["amount_cents"]:
                cancel.append(obj["operation_id"])
                excess -= obj["amount_cents"]
        need += max(0, excess) + sum(o["amount_cents"] for o in credits if o["status"] == "pending")
        for obj in charges:
            available = obj["amount_cents"] - sum(o["amount_cents"] for o in credits if o["parent_id"] == obj["operation_id"])
            quantity = min(max(0, excess), available)
            if obj["status"] == "succeeded" and quantity:
                refunds.append({"charge_id": obj["operation_id"], "amount_cents": quantity, "key": "recovery/" + obj["operation_id"] + "/" + str(result["at_tick"])})
                excess -= quantity
    if cancel:
        return {"command": "cancel", "target": cancel}
    wallet = result["wallet"]
    if need > wallet["available_cents"] and wallet["treasury_cents"]:
        return {"command": "fund", "target": min(wallet["treasury_cents"], need - wallet["available_cents"])}
    if refunds and sum(r["amount_cents"] for r in refunds) <= wallet["available_cents"]:
        return {"command": "refund", "target": refunds}
    if not any(c.get("enabled") is True for c in configs):
        return {"command": "configure", "target": {"enabled": True}}
    if not any(a["command"] == "workload" for a in seen):
        return {"command": "workload", "target": 2}
    if any(o["status"] == "pending" for o in operations):
        return {"command": "provider", "target": "all"}
    return {"command": "inspect", "target": "metrics"}
