"""Open cross-component payment reconciliation repair."""
from .incident import IncidentEnvironment
from .reconciliation_data import PROFILES
from .reconciliation_runtime import Runtime

VERSION = "reconciliation-repair/1"
POLICY = "reconciliation_operator"


def make_case(profile="capture_snapshots"):
    if profile not in PROFILES:
        raise ValueError("Unknown reconciliation contract")
    return {"generator_version": VERSION, "family": "reconciliation_repair", "profile": profile,
            "domain": "payment_operations", "source_task_id": "constructed/reconciliation/"+profile, "max_steps": 80}


def suite():
    return {"generator_version": VERSION, "cases": [make_case(profile) for profile in PROFILES]}


def validate_case(case):
    if case != make_case(case.get("profile")):
        raise ValueError("Unknown reconciliation repair contract")


def healthy(audit):
    return (audit["position_errors"] == 0 and audit["report_errors"] == 0 and audit["pending_receipts"] == 0
            and audit["output_current"] and audit["workload_batches"] >= 2)


class ReconciliationEnvironment(IncidentEnvironment):
    validate_case = staticmethod(validate_case)
    healthy = staticmethod(healthy)

    def __init__(self, case, condition="open", *, recorded_calls=None):
        super().__init__(case, condition, recorded_calls=recorded_calls)
        self.last_result = {"alert": "Merchant payment reconciliation is incorrect after a pipeline release. Diagnose component rules, repair the running pipeline and historical output, test new business, and hand over.", "current_tick": 0}

    def make_runtime(self):
        return Runtime(self.case)

    def contract(self):
        return {"family": "reconciliation_repair", "task": "Deliver correct per-object and per-merchant/currency reconciliation under the documented provider contract. Investigate source and evidence, patch SQL components, deploy and recover materialized output. Exercise at least two new workload batches before verification and explicit handover.",
                "workspace": "Constructed local HTTP provider and separate file-backed SQLite databases; actual SQL transformations over copied public inputs, no arbitrary host code execution.",
                "actions": {"inspect": "target: operations,contract,schema,pipeline,timing,source,metrics",
                            "query": "target: read-only local SQLite SQL, 100-row cap",
                            "provider": "target: all; HTTP authoritative CURRENT per-object positions; does not repair output",
                            "patch": "target: {stage:normalize|resolve|aggregate,sql:SELECT text}; stage one replacement source",
                            "test": "no target; execute staged components on current receipts, return intermediate outputs; no repair",
                            "deploy": "no target; validate and atomically activate staged components; no backfill",
                            "refresh": "no target; atomically rebuild materialized output with active sources",
                            "workload": "target: 1; submit one new business batch, maximum three",
                            "wait": "no target; advance one tick and ingest available feed",
                            "verify": "no target; read-only business verification, no processing or time advancement",
                            "finish": "no target; explicit final handover"},
                "limits": "80 actions including finish. Reads, writes and invalid actions run then advance one tick and ingest available HTTP receipts. Valid verify/finish freeze state. Other actions expire PASS. Read pipeline/timing for execution and timing limits.",
                "success": "Every current economic object, including zero amounts, appears exactly once with correct merchant,currency,net minor units. Merchant/currency totals also match provider truth. No pending receipts; outputs reflect current active sources and all received data; at least two new workload batches; current-state verify PASS then finish. Source text is not graded."}

    def grade(self):
        current = self.last_response
        audit = current["audit"] if current else None
        verified = bool(current and self.verified_state == current["state_sha256"])
        return {"success": bool(self.done and self.reason == "finished" and audit and healthy(audit) and verified),
                "termination": self.reason, "steps": len(self.history), "cost": len(self.history), "budget": self.case["max_steps"],
                "invalid_actions": self.invalid_actions, "verified_current_state": verified,
                **{k: audit[k] if audit else None for k in ("position_errors", "report_errors", "pending_receipts", "output_current", "workload_batches", "business_objects")},
                "http_requests": current["http_requests"] if current else 0}

    def evidence(self):
        evidence = super().evidence()
        evidence["runtime"] = "bounded-sql-http-reconciliation/1"
        return evidence
