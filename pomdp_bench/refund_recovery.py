"""Versioned coupling of source repair, uncertain commitment and refund recovery."""
from .incident import IncidentEnvironment
from .refund_runtime import Runtime

VERSION = "external-settlement/2"
POLICY = "refund_operator"


def make_case():
    return {"generator_version": VERSION, "family": "refund_recovery", "profile": "coupled_rules",
            "domain": "payment_operations", "source_task_id": "adapted/refund-recovery-v1", "max_steps": 100}


def suite():
    return {"generator_version": VERSION, "cases": [make_case()]}


def validate_case(case):
    if case != make_case():
        raise ValueError("Unknown refund recovery contract")


def healthy(audit):
    return (not audit["book_mismatches"] and not audit["external_mismatches"] and not audit["intent_mismatches"]
            and not audit["projection_errors"] and not audit["pending_operations"]
            and not audit["ready_intents"] and not audit["undelivered_events"] and audit["worker_enabled"]
            and not audit["worker_error"] and audit["projection_current"] and audit["workload_batches"] >= 2)


class RefundEnvironment(IncidentEnvironment):
    validate_case = staticmethod(validate_case)
    healthy = staticmethod(healthy)

    def __init__(self, case, condition="open", *, recorded_calls=None):
        super().__init__(case, condition, recorded_calls=recorded_calls)
        self.last_result = {"alert": "Take over partial refund recovery after a rule deployment. The worker is paused. HTTP errors left uncertain provider outcomes and books disagree with approved refunds. Repair components, recover external obligations and hand over.", "current_tick": 0}

    def make_runtime(self):
        return Runtime(self.case)

    def contract(self):
        return {"family": "refund_recovery", "task": "Deliver every approved partial refund exactly, restore local books and leave a working deployment. Investigate public source/data/provider state, repair SQL rules, recover uncertain/failed operations, exercise two new batches and verify. Multiple intents can share one charge; external refunds cannot be reversed or repaired by local edits.",
                "workspace": "Local HTTP provider and separate SQLite databases. Adapted mechanisms from public refund-handling defects, not execution of those upstream applications. No real funds or external accounts.",
                "actions": {"inspect": "target: operations,contract,events,schema,pipeline,timing,source,metrics",
                            "query": "target: local read-only SQLite SQL (100 rows)",
                            "provider": "target: all or 1..32 order IDs; retrieve current operations and finite wallet through HTTP, update local snapshots only",
                            "patch": "target: {stage:decode|project|dispatch,sql:SELECT source}; stage a rule",
                            "test": "no target; execute staged rules on current public data; SQL issues no HTTP, enabled worker still runs at tick end",
                            "deploy": "no target; validate and activate staged rules; no backfill",
                            "refresh": "no target; rebuild refund projection from received callbacks with active rules",
                            "configure": "target: {enabled:bool}; start/pause worker; all behavior fixes require SQL changes",
                            "retry": "target: {intent_id,key?:new key}; reset intent to ready. Different keys may cause duplicate refunds; inspect current provider state",
                            "fund": "target: positive integer cents; move finite treasury to refund reserve",
                            "refund": "target: 1..32 {intent_id,amount_cents,key}; direct provider request bound to an approved intent, retrieve its charge first",
                            "adjust": "target: {order_id,delta_cents,key}; changes local books only",
                            "workload": "target: 1; new charge with two partial refund intents, maximum three batches, minimum two",
                            "wait": "no target; advance one tick",
                            "verify": "no target; read-only current-state checks, no processing/draining",
                            "finish": "no target; explicit handover"},
                "limits": "100 actions including finish. Normal actions run then advance worker, settlement and callbacks one tick. Valid verify/finish freeze business state; other actions expire PASS. Public timing/contract explain delays and failed-operation recovery. No hidden wall-clock business changes.",
                "success": "Each approved intent has exactly its requested external refund, and each provider refund has a correct local operation/order/amount/status/version projection, including failed refunds. External net transfers AND local books equal original charges minus approved obligations for every order. No pending operation, ready intent, undelivered event or worker error. Worker enabled; projection reflects active code and all received callbacks; at least two new batches. Current verify PASS then finish. Excess refunds remain in immutable transfer history; no source-string grading."}

    def grade(self):
        current = self.last_response
        audit = current["audit"] if current else None
        verified = bool(current and self.verified_state == current["state_sha256"])
        return {"success": bool(self.done and self.reason == "finished" and audit and healthy(audit) and verified),
                "termination": self.reason, "steps": len(self.history), "cost": len(self.history), "budget": self.case["max_steps"],
                "invalid_actions": self.invalid_actions, "verified_current_state": verified,
                "book_errors": len(audit["book_mismatches"]) if audit else None,
                "external_errors": len(audit["external_mismatches"]) if audit else None,
                "intent_errors": len(audit["intent_mismatches"]) if audit else None,
                "projection_errors": audit["projection_errors"] if audit else None,
                **{k: audit[k] if audit else None for k in ("excess_refunded_cents", "pending_operations", "ready_intents", "undelivered_events", "worker_enabled", "worker_error", "projection_current", "workload_batches")},
                "http_requests": current["http_requests"] if current else 0}

    def evidence(self):
        evidence = super().evidence()
        evidence["runtime"] = "sql-refund-recovery-http-sqlite/1"
        return evidence
