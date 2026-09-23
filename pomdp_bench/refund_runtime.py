"""SQL repairs drive real external refunds; local rebuilding cannot undo payment.

Reuses the existing provider, settlement clock, liquidity, HTTP, read-only SQL and
action recorder. Public upstream reports inform mechanisms; this is an adaptation,
not execution of those applications or a claimed production incident reproduction.
"""
import json
import sqlite3

from .generator import digest
from .refund_rules import BROKEN, INTERFACES, run
from .settlement_runtime import Runtime as SettlementRuntime

DOCS = {
    "operations": "Refund support has approved several partial refunds. The worker is paused after a bad release. Some HTTP 503s committed refunds; others never reached the provider. Local completion records and callback projections disagree. Repair the deployed SQL rules, recover all approved refunds, exercise two new batches and hand over with processing enabled. The three components are decode, project and dispatch. Inspect source and evidence. Never interpret a local book correction as an external refund.",
    "contract": "refund_intents contains separately approved refund obligations. amount_cents is the amount for THAT intent, not the original charge or a cumulative total. Several intents may share one order and charge. Charges and refund operations have distinct IDs. Provider refund keys identify one external request: same key returns that original object, even if failed, with HTTP 200; a different key creates a new refund subject to the charge's refundable amount. A 503 may occur after commit. Pending refunds reserve charge capacity; only succeeded refunds move money. Insufficient funded reserve causes a terminal failure after four ticks. Refunds cannot be canceled or reversed in this environment. Never recharge a customer to undo an excess refund. Finite treasury must cover all remaining approved refunds; workload adds only its own required treasury.",
    "events": "Delivered receipts contain event_type and body. refund.created is emitted when an operation is created, including already succeeded objects; refund.updated when status changes. Body: operation_id,order_id,amount_cents,charge_cents,status,version,key,parent_id,created_tick,settle_at. amount_cents is that refund; charge_cents is original charge amount. charge.refunded is a cumulative charge summary with order_id,charge_id,charge_cents,amount_refunded,version; it is not another refund. Duplicates may have different receipt IDs, pending events can arrive after terminal events. Operation version determines freshness within the same refund. Separate partial refunds on one charge remain separate economic objects. Current provider reads are authoritative, not old callbacks. Schema intentionally simplifies upstream webhook payloads; no actual provider credentials are used.",
    "schema": "Local tables: refund_intents(intent_id,order_id,charge_id,amount_cents,request_key,state,attempts,last_error), receipts(receipt,event_type,body), rules(stage,active,staged), meta(key,value), intent_keys(intent_id,key), an append-only binding of initial/retried/dispatched/manual request keys to intent ownership. A request key belongs to only one intent; conflicting ownership is rejected before sending the batch. Every intent must receive exactly its approved amount; correct order totals cannot hide swapped allocations. Every provider refund, including failed ones, needs a current local projection. Inherited orders(order_id,amount_cents,is_probe) has expected FINAL customer net debit after approved refunds. projection(operation_id,order_id,kind,amount_cents,status,version), snapshots(operation_id,order_id,kind,amount_cents,key,parent_id,status,version,created_tick,settle_at), books(order_id,amount_cents,book_cents), adjustments(adjustment_id,order_id,delta_cents,key), config(name,value). The provider and future notification queue are separate and inaccessible to local SQL. provider all retrieves authoritative objects and wallet into snapshots, not the projection.",
    "pipeline": "Each source is one SELECT, evaluated with bounded SQLite on copied public input only. decode reads receipts(receipt,event_type,body), returns receipt,operation_id,order_id,amount_cents,status,version. project reads decoded with those columns, returns operation_id,order_id,amount_cents,status,version. dispatch reads queue(intent_id,order_id,charge_id,amount_cents,charge_cents,request_key,attempt) for READY intents, returns intent_id,order_id,charge_id,amount_cents,key. JSON extraction, CTEs, windows, grouping and joins are available; no host files, extensions, ATTACH, clock or oracle. 6000 SQL chars/stage,256 rows,approximately one million VM instructions. patch stages one source; test executes staged SQL without issuing HTTP; deploy validates and activates staged sources without backfilling. Both remain ordinary actions: an enabled worker runs at the end-of-action tick. Pause it to test without outbound work. refresh rebuilds refund projection from all received events with ACTIVE decode/project. Existing charge projection remains. SQL execution is not correctness verification. Worker runs ACTIVE dispatch each normal tick when enabled; successful/accepted HTTP marks an intent submitted, not settled. A 503 leaves it ready. Newly submitted probe intents deliberately lose their first acknowledgement. retry resets selected intents to ready and optionally changes the request key; use current provider evidence before deciding whether a NEW request is needed.",
    "timing": "100 actions including finish. Ordinary reads/changes/rejections act then advance one business tick. Enabled worker dispatches ready intents, due provider operations settle, then due callbacks arrive. Notification delay is at most eight ticks; pending notifications lag terminal ones. No wall-clock-dependent business clock. Initial pending refund settles at tick 4 and fails if reserve is insufficient; failure can be recovered with a newly keyed request. There is no arbitrary cancel-before-inspection deadline. Valid verify/finish spend a step but do not advance, settle or refresh. At least two workload batches required, maximum three; each creates a new charge with TWO separate partial refund intents and matching new treasury. Every other action invalidates PASS.",
}


class Runtime(SettlementRuntime):
    def initialize(self):
        self.connection.executescript("CREATE TABLE refund_intents(intent_id TEXT PRIMARY KEY,order_id TEXT,charge_id TEXT,amount_cents INTEGER,request_key TEXT,state TEXT,attempts INTEGER,last_error TEXT);"
            "CREATE TABLE receipts(receipt INTEGER PRIMARY KEY,event_type TEXT,body TEXT);"
            "CREATE TABLE rules(stage TEXT PRIMARY KEY,active TEXT,staged TEXT);"
            "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);"
            "CREATE TABLE intent_keys(intent_id TEXT,key TEXT UNIQUE,PRIMARY KEY(intent_id,key));")
        self.connection.executemany("INSERT INTO rules VALUES (?,?,?)", [(k, v, v) for k, v in BROKEN.items()])
        self.provider.execute("UPDATE wallet SET treasury_cents=450,available_cents=0")
        for oid, original, amounts in (("order-a", 1000, (150, 100)), ("order-b", 800, (200,)), ("order-c", 600, (150,))):
            charge = self.add_refund_order(oid, original, amounts, False)
            if oid == "order-a":
                self.seed(oid, 150, oid+"/refund-1", "succeeded", kind="refund", parent=charge)
            if oid == "order-b":
                self.seed(oid, 200, oid+"/refund-1", "pending", due=4, kind="refund", parent=charge)
        self.connection.execute("UPDATE refund_intents SET attempts=1,last_error='503: outcome unknown'")
        self.connection.execute("INSERT INTO meta VALUES ('batches','0')")
        self.connection.commit()
        self.provider.commit()

    def add_refund_order(self, oid, original, amounts, probe):
        self.connection.execute("INSERT INTO orders VALUES (?,?,?)", (oid, original-sum(amounts), int(probe)))
        charge = self.seed(oid, original, oid+"/charge", "succeeded")
        self.connection.execute("INSERT INTO projection VALUES (?,?, 'charge',?,'succeeded',1)", (charge, oid, original))
        for n, amount in enumerate(amounts, 1):
            self.connection.execute("INSERT INTO refund_intents VALUES (?,?,?,?,?,'ready',0,NULL)", (oid+"/intent-"+str(n), oid, charge, amount, oid+"/refund-"+str(n)))
            self.connection.execute("INSERT INTO intent_keys VALUES (?,?)", (oid+"/intent-"+str(n), oid+"/refund-"+str(n)))
        return charge

    def notify(self, opid):
        obj = self.object(opid)
        if obj["kind"] == "charge":
            return
        charge = self.object(obj["parent_id"])
        body = {**obj, "charge_cents": charge["amount_cents"]}
        event_type = "refund.created" if obj["version"] == 1 else "refund.updated"
        delay = 7 if obj["status"] == "pending" else 1
        for extra in (0, 1):
            self.provider.execute("INSERT INTO notifications(event_id,deliver_at,body,delivered) VALUES (?,?,?,0)",
                (opid+"/v"+str(obj["version"]), self.tick+delay+extra, json.dumps({"type": event_type, "object": body}, sort_keys=True)))
        if obj["status"] == "succeeded":
            amount = self.provider.execute("SELECT coalesce(sum(amount_cents),0) FROM operations WHERE parent_id=? AND status='succeeded'", (obj["parent_id"],)).fetchone()[0]
            summary = {"order_id": obj["order_id"], "charge_id": obj["parent_id"], "charge_cents": charge["amount_cents"], "amount_refunded": amount, "version": obj["version"]}
            self.provider.execute("INSERT INTO notifications(event_id,deliver_at,body,delivered) VALUES (?,?,?,0)",
                (opid+"/summary", self.tick+2, json.dumps({"type": "charge.refunded", "object": summary}, sort_keys=True)))

    def source(self, column):
        return {r["stage"]: r[column] for r in self.rows("SELECT * FROM rules")}

    def raw(self):
        return [list(r) for r in self.connection.execute("SELECT receipt,event_type,body FROM receipts ORDER BY receipt")]

    def queue(self):
        return [list(r) for r in self.connection.execute("SELECT i.intent_id,i.order_id,i.charge_id,i.amount_cents,p.amount_cents,i.request_key,i.attempts+1 FROM refund_intents i JOIN projection p ON i.charge_id=p.operation_id WHERE i.state='ready' ORDER BY i.intent_id")]

    def outputs(self, column):
        sources = self.source(column)
        decoded = run(sources["decode"], "decode", self.raw())
        return {"decode": decoded, "project": run(sources["project"], "project", decoded),
                "dispatch": run(sources["dispatch"], "dispatch", self.queue())}

    def input_digest(self):
        sources = self.source("active")
        return digest([sources["decode"], sources["project"], self.raw()])

    def refresh(self):
        sources = self.source("active")
        rows = run(sources["project"], "project", run(sources["decode"], "decode", self.raw()))
        with self.connection:
            self.connection.execute("DELETE FROM projection WHERE kind='refund'")
            for opid, oid, amount, status, version in rows:
                if status not in ("pending", "succeeded", "failed", "canceled") or amount < 0:
                    raise ValueError("Invalid projected refund")
                self.connection.execute("INSERT INTO projection VALUES (?,?,'refund',?,?,?)", (opid, oid, amount, status, version))
            self.connection.execute("INSERT OR REPLACE INTO meta VALUES ('materialized',?)", (self.input_digest(),))
        return {"refund_projection_rows": len(rows)}

    def process_outbox(self):
        if not self.settings["enabled"]:
            return
        self.connection.execute("DELETE FROM meta WHERE key='worker_error'")
        try:
            requests = run(self.source("active")["dispatch"], "dispatch", self.queue())
            known = {r[0]: r for r in self.queue()}
            if len({r[0] for r in requests}) != len(requests):
                raise ValueError("dispatch emitted duplicate intent rows")
            for iid, oid, charge, amount, key in requests:
                if iid not in known or (oid, charge) != tuple(known[iid][1:3]) or not 1 <= amount <= 100000:
                    raise ValueError("dispatch needs a ready intent, its order/charge and positive bounded cents")
            self.check_keys([(r[0], r[4]) for r in requests])
        except (ValueError, sqlite3.Error) as exc:
            self.connection.execute("INSERT OR REPLACE INTO meta VALUES ('worker_error',?)", (str(exc)[:300],))
            return
        for iid, oid, charge, amount, key in requests:
            row = known[iid]
            probe = self.connection.execute("SELECT is_probe FROM orders WHERE order_id=?", (oid,)).fetchone()[0]
            self.connection.execute("INSERT OR IGNORE INTO intent_keys VALUES (?,?)", (iid, key))
            status, response = self.http("/refund", {"order_id": oid, "parent_id": charge, "amount_cents": amount, "key": key,
                                                     "lose_ack": bool(probe and row[-1] == 1)})
            self.connection.execute("UPDATE refund_intents SET attempts=attempts+1,state=?,last_error=? WHERE intent_id=?",
                                    ("submitted" if status in (200, 202) else "ready", response.get("error"), iid))

    def check_keys(self, bindings):
        owners = {r["key"]: r["intent_id"] for r in self.rows("SELECT * FROM intent_keys")}
        for iid, key in bindings:
            if not 1 <= len(key) <= 120 or key in owners and owners[key] != iid:
                raise ValueError("Each bounded request key belongs to exactly one refund intent")
            owners[key] = iid

    def deliver_events(self):
        for event in self.prows("SELECT * FROM notifications WHERE delivered=0 AND deliver_at<=? ORDER BY deliver_at,sequence", (self.tick,)):
            payload = json.loads(event["body"])
            self.connection.execute("INSERT INTO receipts(event_type,body) VALUES (?,?)", (payload["type"], json.dumps(payload["object"], sort_keys=True)))
            self.provider.execute("UPDATE notifications SET delivered=1 WHERE sequence=?", (event["sequence"],))

    def audit(self):
        mismatches, external = [], []
        excess = 0
        for row in self.rows("SELECT * FROM books ORDER BY order_id"):
            actual = self.provider.execute("SELECT coalesce(sum(delta_cents),0) FROM transfers WHERE order_id=?", (row["order_id"],)).fetchone()[0]
            if row["book_cents"] != row["amount_cents"]:
                mismatches.append(row)
            if actual != row["amount_cents"]:
                external.append({"order_id": row["order_id"], "expected_net_cents": row["amount_cents"], "actual_net_cents": actual})
            excess += max(0, row["amount_cents"]-actual)
        materialized = self.connection.execute("SELECT value FROM meta WHERE key='materialized'").fetchone()
        intent_mismatches = []
        for intent in self.rows("SELECT * FROM refund_intents ORDER BY intent_id"):
            keys = [r["key"] for r in self.rows("SELECT key FROM intent_keys WHERE intent_id=?", (intent["intent_id"],))]
            actual = self.provider.execute("SELECT coalesce(sum(-t.delta_cents),0) FROM transfers t JOIN operations o USING(operation_id) WHERE o.kind='refund' AND o.key IN ("+','.join('?' for _ in keys)+")", keys).fetchone()[0]
            if actual != intent["amount_cents"]:
                intent_mismatches.append({"intent_id": intent["intent_id"], "expected_cents": intent["amount_cents"], "actual_cents": actual})
        expected_projection = {r["operation_id"]: (r["order_id"], r["amount_cents"], r["status"], r["version"])
                               for r in self.prows("SELECT * FROM operations WHERE kind='refund'")}
        actual_projection = {r["operation_id"]: (r["order_id"], r["amount_cents"], r["status"], r["version"])
                             for r in self.rows("SELECT * FROM projection WHERE kind='refund'")}
        return {"book_mismatches": mismatches, "external_mismatches": external, "excess_refunded_cents": excess,
                "intent_mismatches": intent_mismatches,
                "projection_errors": sum(expected_projection.get(k) != actual_projection.get(k) for k in expected_projection.keys() | actual_projection.keys()),
                "pending_operations": self.provider.execute("SELECT count(*) FROM operations WHERE status='pending'").fetchone()[0],
                "ready_intents": self.connection.execute("SELECT count(*) FROM refund_intents WHERE state='ready'").fetchone()[0],
                "undelivered_events": self.provider.execute("SELECT count(*) FROM notifications WHERE delivered=0").fetchone()[0],
                "worker_enabled": self.settings["enabled"], "worker_error": bool(self.rows("SELECT * FROM meta WHERE key='worker_error'")),
                "projection_current": bool(materialized and materialized[0] == self.input_digest()),
                "workload_batches": int(self.connection.execute("SELECT value FROM meta WHERE key='batches'").fetchone()[0])}

    def tables(self):
        data = super().tables()
        for table in ("refund_intents", "receipts", "rules", "meta", "intent_keys"):
            data["local"][table] = self.rows(f"SELECT * FROM {table} ORDER BY 1")
        return data

    def operate(self, command, target):
        if command == "inspect":
            if target in DOCS:
                return {"text": DOCS[target]}
            if target == "source":
                return {"rules": self.rows("SELECT * FROM rules ORDER BY stage"), "interfaces": {s: {k: list(v) if isinstance(v, tuple) else v for k, v in shape.items()} for s, shape in INTERFACES.items()}}
            if target == "metrics":
                return {"enabled": self.settings["enabled"], "ready_intents": self.audit()["ready_intents"],
                        "undelivered_events": self.audit()["undelivered_events"], "worker_error": self.rows("SELECT value FROM meta WHERE key='worker_error'"),
                        "projection_current": self.audit()["projection_current"]}
            raise ValueError("inspect operations,contract,events,schema,pipeline,timing,source,metrics")
        if command == "patch":
            if (not isinstance(target, dict) or set(target) != {"stage", "sql"} or target["stage"] not in INTERFACES
                    or not isinstance(target["sql"], str) or not 1 <= len(target["sql"]) <= 6000):
                raise ValueError("patch takes {stage:decode|project|dispatch,sql:SELECT text}")
            self.connection.execute("UPDATE rules SET staged=? WHERE stage=?", (target["sql"], target["stage"]))
            return {"staged": target["stage"]}
        if command in ("test", "deploy") and target is None:
            output = self.outputs("staged")
            if command == "test":
                return {"execution_ok": True, "outputs": output, "sql_external_mutations": False}
            self.connection.execute("UPDATE rules SET active=staged")
            return {"deployed": True, "backfill_performed": False}
        if command == "refresh" and target is None:
            return self.refresh()
        if command == "configure":
            if not isinstance(target, dict) or set(target) != {"enabled"} or type(target["enabled"]) is not bool:
                raise ValueError("configure takes {enabled:bool}; repair behavior through SQL source")
            self.settings["enabled"] = target["enabled"]
            self.save_config()
            return {"enabled": target["enabled"]}
        if command == "retry":
            if (not isinstance(target, dict) or set(target) - {"intent_id", "key"} or not isinstance(target.get("intent_id"), str)
                    or "key" in target and (not isinstance(target["key"], str) or not 1 <= len(target["key"]) <= 120)):
                raise ValueError("retry takes {intent_id,key?:new request key}; new key can duplicate an existing refund")
            old = self.connection.execute("SELECT request_key FROM refund_intents WHERE intent_id=?", (target["intent_id"],)).fetchone()
            if not old:
                raise ValueError("Unknown refund intent")
            self.check_keys([(target["intent_id"], target.get("key", old[0]))])
            self.connection.execute("UPDATE refund_intents SET state='ready',request_key=?,last_error=NULL WHERE intent_id=?", (target.get("key", old[0]), target["intent_id"]))
            self.connection.execute("INSERT OR IGNORE INTO intent_keys VALUES (?,?)", (target["intent_id"], target.get("key", old[0])))
            return {"ready": target["intent_id"]}
        if command == "refund":
            if not isinstance(target, list) or not 1 <= len(target) <= 32:
                raise ValueError("refund takes 1..32 {intent_id,amount_cents,key} requests")
            bound = []
            for item in target:
                if (not isinstance(item, dict) or set(item) != {"intent_id", "amount_cents", "key"}
                        or not isinstance(item["intent_id"], str) or type(item["amount_cents"]) is not int
                        or not 1 <= item["amount_cents"] <= 100000 or not isinstance(item["key"], str) or not 1 <= len(item["key"]) <= 120):
                    raise ValueError("Invalid intent-bound refund request")
                intent = self.connection.execute("SELECT charge_id FROM refund_intents WHERE intent_id=?", (item["intent_id"],)).fetchone()
                if not intent:
                    raise ValueError("Unknown intent")
                bound.append({"charge_id": intent[0], "amount_cents": item["amount_cents"], "key": item["key"]})
            self.check_keys([(item["intent_id"], item["key"]) for item in target])
            result = super().operate("refund", bound)
            for item in target:
                self.connection.execute("INSERT OR IGNORE INTO intent_keys VALUES (?,?)", (item["intent_id"], item["key"]))
            return result
        if command == "workload" and type(target) is int and target == 1:
            number = self.audit()["workload_batches"]+1
            if number > 3:
                raise ValueError("At most three probe batches")
            amounts = (60+number*7, 30+number*3)
            oid = "probe-"+str(number)
            self.add_refund_order(oid, 500+53*number, amounts, True)
            self.provider.execute("UPDATE wallet SET treasury_cents=treasury_cents+?", (sum(amounts),))
            self.provider.commit()
            self.connection.execute("UPDATE meta SET value=? WHERE key='batches'", (str(number),))
            return {"accepted_order": oid, "new_refund_treasury_cents": sum(amounts)}
        if command == "verify" and target is None:
            from .refund_recovery import healthy
            audit = self.audit()
            return {"passed": healthy(audit), **audit}
        if command in ("query", "provider", "fund", "adjust", "wait", "finish"):
            return super().operate(command, target)
        raise ValueError("Unknown action or target; consult the public contract")
