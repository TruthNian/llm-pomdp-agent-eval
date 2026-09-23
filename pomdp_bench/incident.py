"""Open incident response over executable local services, with recorded-call replay."""
import copy

from .generator import digest
from .incident_runtime import Runtime

VERSION = "service-incident/1"
POLICY = "incident_operator"


def make_case():
    return {"generator_version": VERSION, "family": "service_incident", "profile": "settlement_release",
            "domain": "payment_operations", "source_task_id": "constructed/settlement-release-v1",
            "max_steps": 60}


def suite():
    return {"generator_version": VERSION, "cases": [make_case()]}


def validate_case(case):
    if case != make_case():
        raise ValueError("Unknown incident contract; version new scenarios explicitly")


def healthy(audit):
    return (not audit["mismatches"] and audit["unsettled_messages"] == 0
            and audit["monitoring_intact"] and audit["worker_enabled"])


class IncidentEnvironment:
    validate_case = staticmethod(validate_case)
    healthy = staticmethod(healthy)

    def make_runtime(self):
        return Runtime(self.case)

    def __init__(self, case, condition="open", *, recorded_calls=None):
        self.validate_case(case)
        if condition != "open":
            raise ValueError("The executable incident currently supports open only")
        self.case, self.condition = case, condition
        self.history, self.calls = [], []
        self.recorded_calls = recorded_calls
        self.runtime = None
        self.done, self.reason = False, None
        self.verified_state = None
        self.last_response = None
        self.last_result = {"alert": "Checkout accepts requests, but settlement complaints increased after a release. Take over the incident."}
        self.invalid_actions = 0

    def contract(self):
        return {"family": "service_incident", "task": "Restore payment settlement and hand over a healthy service. "
                "Protect every accepted order from loss or duplicate net debit, including historical backlog and new traffic. "
                "Leave processing and monitoring enabled. You decide what to inspect, change, retry and verify.",
                "workspace": "Local HTTP checkout/ledger services and a durable SQLite outbox. No real money or external accounts.",
                "actions": {
                    "inspect": "target: operations, schema, deployment, ledger-contract, worker, traffic, tools, config, metrics, logs",
                    "query": "target: one read-only SQLite query, joins and aggregation supported; up to 100 rows",
                    "configure": "target: {service: worker|monitor, patch: configuration object}; inspect tools for types",
                    "restart": "target: worker; activates staged configuration",
                    "rollback": "target: worker; restores the prior deployment's active configuration",
                    "replay": "target: 1..32 message_id strings; resend preserved messages",
                    "rebuild": "target: 1..32 message_id strings; regenerate from authoritative orders",
                    "adjust": "target: 1..32 {order_id,delta_cents,entry_ids} corrections; inspect ledger-contract",
                    "workload": "target: integer 1..8; submit new orders and process a batch",
                    "verify": "no target; send new traffic, test retry behavior and reconcile all actual order/ledger rows",
                    "finish": "no target; final handover"},
                "limits": "60 action ticks including finish. Reads, invalid actions and changes each use a tick. "
                "Traffic/processing advance between operations; inspect traffic for the schedule. "
                "Read-only SQL cannot mutate data; operator changes use the declared interfaces.",
                "success": "All accepted orders reconcile exactly, no unresolved outbox, processing and monitoring enabled; "
                "verify must PASS at the current service state and be followed by finish. Subsequent operations expire PASS."}

    def observation(self):
        return {"steps_remaining": self.case["max_steps"] - len(self.history), "result": copy.deepcopy(self.last_result),
                "verification_current": self.verified_state is not None, "done": self.done}

    def lower_bound(self):
        return None

    def step(self, action):
        if self.done:
            raise RuntimeError("Episode already ended")
        action = copy.deepcopy(action)
        request_hash = digest([self.case["generator_version"], self.case, len(self.calls), action])
        if self.recorded_calls is not None:
            if len(self.calls) >= len(self.recorded_calls):
                raise ValueError("Missing recorded service response")
            call = copy.deepcopy(self.recorded_calls[len(self.calls)])
            if call["request_sha256"] != request_hash or call["action"] != action:
                raise ValueError("Incident action/response binding changed")
            response = call["response"]
        else:
            if self.runtime is None:
                self.runtime = self.make_runtime()
            if not isinstance(action, dict):
                action_for_runtime = {"command": "invalid", "target": action}
            else:
                action_for_runtime = action
            response = self.runtime.call(action_for_runtime)
            call = {"request_sha256": request_hash, "action": action, "response": response}
        self.calls.append(call)
        self.last_response = response
        self.last_result = response["result"]
        command = action.get("command") if isinstance(action, dict) else None
        if "error" in self.last_result:
            self.invalid_actions += 1
        if command == "finish" and self.last_result.get("handover"):
            self.done, self.reason = True, "finished"
        else:
            self.verified_state = (response["state_sha256"] if command == "verify"
                                   and self.last_result.get("passed") and self.healthy(response["audit"]) else None)
        if len(self.history) + 1 >= self.case["max_steps"] and not self.done:
            self.done, self.reason = True, "step_limit"
        self.history.append({"action": action, "observation": None})
        self.history[-1]["observation"] = self.observation()
        return copy.deepcopy(self.history[-1]["observation"])

    def grade(self):
        current = self.last_response
        audit = current["audit"] if current else None
        verified = bool(current and self.verified_state == current["state_sha256"])
        return {"success": bool(self.done and self.reason == "finished" and audit and self.healthy(audit) and verified),
                "termination": self.reason, "cost": len(self.history), "steps": len(self.history), "budget": self.case["max_steps"],
                "verified_current_state": verified, "invalid_actions": self.invalid_actions,
                "accounting_mismatches": len(audit["mismatches"]) if audit else None,
                "unsettled_messages": audit["unsettled_messages"] if audit else None,
                "monitoring_intact": audit["monitoring_intact"] if audit else None,
                "excess_debit_cent_ticks": sum(sum(max(0, m["ledger_cents"] - m["amount_cents"])
                                                      for m in c["response"]["audit"]["mismatches"]) for c in self.calls),
                "unsettled_message_ticks": sum(c["response"]["audit"]["unsettled_messages"] for c in self.calls),
                "http_requests": current["http_requests"] if current else 0}

    def abort(self, reason="adapter_error"):
        self.done, self.reason = True, reason

    def evidence(self):
        return {"runtime": "stdlib-http-sqlite/1", "calls": copy.deepcopy(self.calls)}

    def close(self):
        if self.runtime is not None:
            self.runtime.close()


def policy_action(request):
    """Runbook-aware competent operator; uses only public observations/SQL rows.

    This is a scripted ceiling control, not a model or an optimality claim.
    """
    history = request["history"]
    if not history:
        return {"command": "inspect", "target": "operations"}
    last = history[-1]
    action, result = last["action"], last["observation"]["result"]
    seen = [e["action"] for e in history]
    for doc in ("schema", "deployment", "ledger-contract", "worker", "config"):
        if {"command": "inspect", "target": doc} not in seen:
            return {"command": "inspect", "target": doc}
    if not any(a["command"] == "configure" for a in seen):
        return {"command": "configure", "target": {"service": "worker", "patch": {"protocol": "compatible", "dedupe": "order", "enabled": True, "batch": 16}}}
    if not any(a["command"] == "restart" for a in seen):
        return {"command": "restart", "target": "worker"}
    if not any(a["command"] == "rebuild" for a in seen):
        if action["command"] == "query":
            ids = [r[0] for r in result["rows"]]
            if ids:
                return {"command": "rebuild", "target": ids}
        return {"command": "query", "target": "SELECT message_id,payload,last_error FROM outbox WHERE state='dead' ORDER BY message_id"}
    if action["command"] == "verify" and result.get("passed"):
        return {"command": "finish"}
    if action["command"] == "query" and result.get("columns", [None])[0] == "order_id":
        fixes = [{"order_id": r[0], "delta_cents": r[1], "entry_ids": [int(x) for x in r[2].split(",")]} for r in result["rows"]]
        return {"command": "adjust", "target": fixes} if fixes else {"command": "verify"}
    if action["command"] == "adjust":
        return {"command": "verify"}
    return {"command": "query", "target": "SELECT o.order_id,o.amount_cents-sum(l.amount_cents) AS delta,group_concat(l.entry_id) AS evidence FROM orders o JOIN ledger l USING(order_id) GROUP BY o.order_id HAVING sum(l.amount_cents)!=o.amount_cents ORDER BY o.order_id"}
