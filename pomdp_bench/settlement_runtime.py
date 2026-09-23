"""Constructed external settlement: two databases, actual HTTP, irreversible history.

The provider database and its future notifications are inaccessible to local SQL.
Only the declared provider API projects current operation state to the operator.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading

from .generator import digest
from .service_io import ServiceIO

DOCS = {
    "operations": "Checkout obligations must reconcile both externally and locally. The worker is paused after a retry deployment. Some failed HTTP requests committed, others never reached the provider. Fixing retry configuration does not cancel existing duplicate operations. A finite treasury can fund refunds; cancellation of still-pending charges does not spend it. Read provider-contract, schema, and timing. This is a constructed local system, not a real payment provider.",
    "provider-contract": "provider retrieves ALL authoritative operations for selected order IDs (or all) through HTTP and replaces their local snapshots. It does not repair books. Operation fields: operation_id,order_id,kind(charge/refund),amount_cents,key,parent_id,status(pending/succeeded/failed/canceled),version,created_tick,settle_at. Same-key submission returns the existing object, including failed/canceled objects; a different key creates a distinct operation. Refunds reference a succeeded charge and cannot exceed its unrefunded amount, counting pending refunds. On their settlement tick they succeed only with enough funded reserve; otherwise they fail terminally. Retrying a failed refund requires a new key. Cancel works only while a charge is pending; settled history cannot be erased. HTTP 503 can mean committed but acknowledgement lost. Current provider reads, not event arrival order, establish the state.",
    "schema": "Local read-only SQL: orders(order_id,amount_cents,is_probe), outbox(message_id,order_id,request_key,state,attempts,last_error), events(receipt_id,event_id,operation_id,order_id,kind,amount_cents,status,version), projection(operation_id,order_id,kind,amount_cents,status,version), snapshots(operation_id,order_id,kind,amount_cents,key,parent_id,status,version,created_tick,settle_at), adjustments(adjustment_id,order_id,delta_cents,key), config(name,value). books is a VIEW summing succeeded projection charges minus refunds plus local adjustments by order. The provider database and undelivered payloads are not SQL-accessible. snapshots are authoritative only at the tick of their last provider retrieval. Joins, aggregation and sqlite_master are available; 100-row result cap.",
    "worker": "configure patches active settings immediately: enabled(bool), retry_identity(stable/attempt), event_order(version/arrival). Stable retries reuse outbox.request_key; attempt retries append an attempt number, even if the original request committed. An HTTP success marks the outbox delivered, not financially settled. Each normal tick processes every ready outbox item once when enabled. Rejected/503 deliveries remain ready. Every probe loses its first charge acknowledgement after commit. Events always arrive even when the worker is paused. version ignores an event older than the stored object; arrival overwrites with every arrival. Existing projections are not automatically rebuilt after config changes. Local adjust changes books only; it never refunds a customer.",
    "timing": "Each normal action, including reads and invalid actions, acts at the current tick and then advances ONE business tick, processing retries, due settlements and event deliveries. Charges and refunds normally settle four ticks after creation. An object can be canceled only before its settle_at boundary. Notifications can arrive duplicated/out of order, up to eight ticks after a transition; inspect metrics for outstanding notification count. The initial alert has a charge reaching its settlement boundary at tick 12. No automatic new orders arrive. workload explicitly submits 1..4 probes; at least two must settle correctly before handover. verify and finish are read-only stable boundaries: they spend an action but neither advance time nor drain anything. Use wait (one tick) to allow outstanding work to progress. Deadline: 80 actions including finish. Business ticks are not production seconds.",
}

LOCAL_SCHEMA = """
CREATE TABLE orders(order_id TEXT PRIMARY KEY, amount_cents INTEGER, is_probe INTEGER);
CREATE TABLE outbox(message_id TEXT PRIMARY KEY, order_id TEXT, request_key TEXT, state TEXT, attempts INTEGER, last_error TEXT);
CREATE TABLE events(receipt_id INTEGER PRIMARY KEY, event_id TEXT, operation_id TEXT, order_id TEXT, kind TEXT, amount_cents INTEGER, status TEXT, version INTEGER);
CREATE TABLE projection(operation_id TEXT PRIMARY KEY, order_id TEXT, kind TEXT, amount_cents INTEGER, status TEXT, version INTEGER);
CREATE TABLE snapshots(operation_id TEXT PRIMARY KEY, order_id TEXT, kind TEXT, amount_cents INTEGER, key TEXT, parent_id TEXT, status TEXT, version INTEGER, created_tick INTEGER, settle_at INTEGER);
CREATE TABLE adjustments(adjustment_id INTEGER PRIMARY KEY, order_id TEXT, delta_cents INTEGER, key TEXT UNIQUE);
CREATE TABLE config(name TEXT PRIMARY KEY, value TEXT);
CREATE VIEW books AS SELECT o.order_id, o.amount_cents,
    coalesce((SELECT sum(CASE WHEN p.kind='charge' THEN p.amount_cents ELSE -p.amount_cents END)
              FROM projection p WHERE p.order_id=o.order_id AND p.status='succeeded'),0)
    +coalesce((SELECT sum(a.delta_cents) FROM adjustments a WHERE a.order_id=o.order_id),0) AS book_cents
    FROM orders o;
"""
PROVIDER_SCHEMA = """
CREATE TABLE operations(operation_id TEXT PRIMARY KEY, order_id TEXT, kind TEXT, amount_cents INTEGER,
    key TEXT UNIQUE, parent_id TEXT, status TEXT, version INTEGER, created_tick INTEGER, settle_at INTEGER);
CREATE TABLE notifications(sequence INTEGER PRIMARY KEY, event_id TEXT, deliver_at INTEGER, body TEXT, delivered INTEGER);
CREATE TABLE transfers(sequence INTEGER PRIMARY KEY, operation_id TEXT UNIQUE, order_id TEXT, delta_cents INTEGER, tick INTEGER);
CREATE TABLE wallet(id INTEGER PRIMARY KEY, available_cents INTEGER, treasury_cents INTEGER);
INSERT INTO wallet VALUES(1,0,800);
"""
LOCAL_TABLES = ("orders", "outbox", "events", "projection", "snapshots", "adjustments", "config")
PROVIDER_TABLES = ("operations", "notifications", "transfers", "wallet")


class Runtime(ServiceIO):
    def __init__(self, case):
        self.case = case
        self.temp = tempfile.TemporaryDirectory(prefix="pomdp-external-")
        self.db = Path(self.temp.name) / "local.sqlite"
        self.connection = sqlite3.connect(self.db, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.provider = sqlite3.connect(Path(self.temp.name) / "provider.sqlite", check_same_thread=False)
        self.provider.row_factory = sqlite3.Row
        self.connection.executescript(LOCAL_SCHEMA)
        self.provider.executescript(PROVIDER_SCHEMA)
        self.tick = self.http_requests = 0
        self.closed = False
        self.lock = threading.RLock()
        self.settings = {"enabled": False, "retry_identity": "attempt", "event_order": "arrival"}
        self.save_config()
        runtime = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with runtime.lock:
                    status, result = runtime.endpoint(self.path, body)
                raw = json.dumps(result).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        self.thread.start()
        try:
            for oid, amount in (("order-a", 1200), ("order-b", 800), ("order-c", 600), ("order-d", 700)):
                self.add_order(oid, amount, False)
            self.seed("order-a", 1200, "order-a/request", "succeeded")
            self.seed("order-a", 1200, "order-a/retry", "pending",
                      due=None if case["profile"] == "no_cancel_deadline" else 12)
            self.seed("order-b", 800, "order-b/request", "succeeded")
            duplicate = self.seed("order-b", 800, "order-b/retry", "succeeded")
            self.seed("order-b", 800, "order-b/refund", "pending", due=4, kind="refund", parent=duplicate)
            self.seed("order-d", 700, "order-d/request", "pending", due=8)
            self.connection.execute("UPDATE outbox SET state='done' WHERE order_id IN ('order-a','order-b')")
            self.connection.execute("UPDATE outbox SET last_error='503: outcome unknown',attempts=1 WHERE state='ready'")
            self.connection.commit()
            self.provider.commit()
        except BaseException:
            self.close()
            raise

    def prows(self, sql, values=()):
        return [dict(r) for r in self.provider.execute(sql, values)]

    def save_config(self):
        for name, value in self.settings.items():
            self.connection.execute("INSERT OR REPLACE INTO config VALUES (?,?)", (name, json.dumps(value)))
        self.connection.commit()

    def add_order(self, oid, amount, probe):
        self.connection.execute("INSERT INTO orders VALUES (?,?,?)", (oid, amount, int(probe)))
        self.connection.execute("INSERT INTO outbox VALUES (?,?,?,'ready',0,NULL)", ("msg-" + oid, oid, oid + "/request"))
        self.connection.commit()

    def seed(self, oid, amount, key, status, *, due=None, kind="charge", parent=None):
        opid = "op-" + str(self.provider.execute("SELECT count(*) FROM operations").fetchone()[0] + 1)
        self.provider.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,1,?,?)",
                              (opid, oid, kind, amount, key, parent, status, self.tick, due))
        if status == "succeeded":
            self.provider.execute("INSERT INTO transfers(operation_id,order_id,delta_cents,tick) VALUES (?,?,?,?)",
                                  (opid, oid, amount if kind == "charge" else -amount, self.tick))
        self.notify(opid)
        self.provider.commit()
        return opid

    def object(self, opid):
        rows = self.prows("SELECT * FROM operations WHERE operation_id=?", (opid,))
        return rows[0] if rows else None

    def notify(self, opid):
        obj = self.object(opid)
        # Pending notifications deliberately lag terminal ones. The two copies
        # have the same event identity; receipt identity belongs to the consumer.
        delay = 0 if self.case["profile"] == "immediate_events" else (7 if obj["status"] == "pending" else 1)
        eid = opid + "/v" + str(obj["version"])
        for extra in (0, 1):
            self.provider.execute("INSERT INTO notifications(event_id,deliver_at,body,delivered) VALUES (?,?,?,0)",
                                  (eid, self.tick + delay + (extra if delay else 0), json.dumps(obj, sort_keys=True)))

    def endpoint(self, path, body):
        if path == "/objects":
            ids = body["order_ids"]
            objects = self.prows("SELECT * FROM operations ORDER BY operation_id")
            return 200, {"at_tick": self.tick, "operations": [o for o in objects if o["order_id"] in ids],
                         "wallet": self.prows("SELECT available_cents,treasury_cents FROM wallet")[0]}
        if path == "/fund":
            amount = body["amount_cents"]
            wallet = self.prows("SELECT * FROM wallet")[0]
            if amount > wallet["treasury_cents"]:
                return 409, {"error": "insufficient treasury; there is no other funding source"}
            with self.provider:
                self.provider.execute("UPDATE wallet SET available_cents=available_cents+?,treasury_cents=treasury_cents-?", (amount, amount))
            return 200, {"funded_cents": amount}
        if path == "/cancel":
            obj = self.object(body["operation_id"])
            if obj is None or obj["kind"] != "charge" or obj["status"] not in ("pending", "canceled"):
                return 409, {"error": "only pending charges can be canceled"}
            if obj["status"] == "pending":
                with self.provider:
                    self.provider.execute("UPDATE operations SET status='canceled',version=version+1 WHERE operation_id=?", (obj["operation_id"],))
                    self.notify(obj["operation_id"])
            return 200, self.object(obj["operation_id"])
        if path in ("/charge", "/refund"):
            oid, amount, key = body["order_id"], body["amount_cents"], body["key"]
            kind = path[1:]
            parent = body.get("parent_id")
            existing = self.prows("SELECT * FROM operations WHERE key=?", (key,))
            if existing:
                old = existing[0]
                if (old["order_id"], old["amount_cents"], old["kind"], old["parent_id"]) != (oid, amount, kind, parent):
                    return 409, {"error": "idempotency key conflicts with original request"}
                return 200, old
            if kind == "refund":
                charge = self.object(parent)
                if not charge or charge["kind"] != "charge" or charge["status"] != "succeeded" or charge["order_id"] != oid:
                    return 409, {"error": "refund needs a succeeded charge for this order"}
                reserved = self.provider.execute("SELECT coalesce(sum(amount_cents),0) FROM operations WHERE parent_id=? AND status IN ('pending','succeeded')", (parent,)).fetchone()[0]
                if reserved + amount > charge["amount_cents"]:
                    return 409, {"error": "refund exceeds unrefunded charge amount"}
            opid = self.seed(oid, amount, key, "pending", due=self.tick + 4, kind=kind, parent=parent)
            if body.get("lose_ack"):
                return 503, {"error": "acknowledgement lost; outcome unknown"}
            return 202, self.object(opid)
        return 404, {"error": "unknown endpoint"}

    def advance(self):
        self.tick += 1
        if self.settings["enabled"]:
            for row in self.rows("SELECT b.*,o.amount_cents,o.is_probe FROM outbox b JOIN orders o USING(order_id) WHERE state='ready' ORDER BY message_id"):
                attempt = row["attempts"] + 1
                key = row["request_key"] if self.settings["retry_identity"] == "stable" else row["request_key"] + "/attempt-" + str(attempt)
                status, result = self.http("/charge", {"order_id": row["order_id"], "amount_cents": row["amount_cents"],
                                                      "key": key, "lose_ack": bool(row["is_probe"] and attempt == 1)})
                self.connection.execute("UPDATE outbox SET attempts=?,state=?,last_error=? WHERE message_id=?",
                                        (attempt, "done" if status in (200, 202) else "ready", result.get("error"), row["message_id"]))
        for obj in self.prows("SELECT * FROM operations WHERE status='pending' AND settle_at<=? ORDER BY operation_id", (self.tick,)):
            enough = obj["kind"] == "charge" or self.provider.execute("SELECT available_cents FROM wallet").fetchone()[0] >= obj["amount_cents"]
            self.provider.execute("UPDATE operations SET status=?,version=version+1 WHERE operation_id=?", ("succeeded" if enough else "failed", obj["operation_id"]))
            if enough:
                amount = obj["amount_cents"] * (1 if obj["kind"] == "charge" else -1)
                self.provider.execute("INSERT INTO transfers(operation_id,order_id,delta_cents,tick) VALUES (?,?,?,?)", (obj["operation_id"], obj["order_id"], amount, self.tick))
                if obj["kind"] == "refund":
                    self.provider.execute("UPDATE wallet SET available_cents=available_cents-?", (obj["amount_cents"],))
            self.notify(obj["operation_id"])
        for event in self.prows("SELECT * FROM notifications WHERE delivered=0 AND deliver_at<=? ORDER BY deliver_at,sequence", (self.tick,)):
            obj = json.loads(event["body"])
            fields = tuple(obj[k] for k in ("operation_id", "order_id", "kind", "amount_cents", "status", "version"))
            self.connection.execute("INSERT INTO events(event_id,operation_id,order_id,kind,amount_cents,status,version) VALUES (?,?,?,?,?,?,?)", (event["event_id"], *fields))
            old = self.connection.execute("SELECT version FROM projection WHERE operation_id=?", (obj["operation_id"],)).fetchone()
            if not old or self.settings["event_order"] == "arrival" or obj["version"] >= old[0]:
                self.connection.execute("INSERT OR REPLACE INTO projection VALUES (?,?,?,?,?,?)", fields)
            self.provider.execute("UPDATE notifications SET delivered=1 WHERE sequence=?", (event["sequence"],))
        self.connection.commit()
        self.provider.commit()

    def audit(self):
        mismatches, external = [], []
        for row in self.rows("SELECT * FROM books ORDER BY order_id"):
            actual = self.provider.execute("SELECT coalesce(sum(delta_cents),0) FROM transfers WHERE order_id=?", (row["order_id"],)).fetchone()[0]
            if row["book_cents"] != row["amount_cents"]:
                mismatches.append(row)
            if actual != row["amount_cents"]:
                external.append({"order_id": row["order_id"], "amount_cents": row["amount_cents"], "external_cents": actual})
        gross_excess = sum(max(0, self.provider.execute("SELECT coalesce(sum(delta_cents),0) FROM transfers WHERE order_id=? AND delta_cents>0", (r["order_id"],)).fetchone()[0] - r["amount_cents"]) for r in self.rows("SELECT * FROM orders"))
        return {"book_mismatches": mismatches, "external_mismatches": external,
                "pending_operations": self.provider.execute("SELECT count(*) FROM operations WHERE status='pending'").fetchone()[0],
                "unsettled_messages": self.connection.execute("SELECT count(*) FROM outbox WHERE state!='done'").fetchone()[0],
                "undelivered_events": self.provider.execute("SELECT count(*) FROM notifications WHERE delivered=0").fetchone()[0],
                "additional_excess_settled_cents": gross_excess - 800,
                "worker_enabled": self.settings["enabled"],
                "probe_orders": self.connection.execute("SELECT count(*) FROM orders WHERE is_probe=1").fetchone()[0],
                "order_count": self.connection.execute("SELECT count(*) FROM orders").fetchone()[0]}

    def tables(self):
        return {"local": {t: self.rows(f"SELECT * FROM {t} ORDER BY 1") for t in LOCAL_TABLES},
                "provider": {t: self.prows(f"SELECT * FROM {t} ORDER BY 1") for t in PROVIDER_TABLES}}

    def ids(self, target, table, column):
        if not isinstance(target, list) or not 1 <= len(target) <= 32 or any(not isinstance(x, str) for x in target) or len(set(target)) != len(target):
            raise ValueError("Select 1..32 distinct IDs")
        rows = self.rows(f"SELECT {column} FROM {table}")
        if set(target) - {r[column] for r in rows}:
            raise ValueError("Unknown local ID")
        return target

    def operate(self, command, target):
        if command == "inspect":
            if target in DOCS:
                text = DOCS[target]
                if target == "timing" and self.case["profile"] == "no_cancel_deadline":
                    text = text.replace("The initial alert has a charge reaching its settlement boundary at tick 12.", "The initial duplicate has no automatic settlement boundary in this ablation; other operations retain normal timing.")
                return {"text": text}
            if target == "config":
                return dict(self.settings)
            if target == "metrics":
                return {"tick": self.tick, "outbox": self.rows("SELECT state,count(*) AS count FROM outbox GROUP BY state"),
                        "undelivered_events": self.provider.execute("SELECT count(*) FROM notifications WHERE delivered=0").fetchone()[0],
                        "settings": dict(self.settings)}
            raise ValueError("inspect: operations, provider-contract, schema, worker, timing, config, metrics")
        if command == "query":
            return self.query(target)
        if command == "configure":
            if not isinstance(target, dict) or not target or target.keys() - self.settings.keys():
                raise ValueError("configure takes enabled, retry_identity and/or event_order")
            for key, value in target.items():
                if (key == "enabled" and type(value) is not bool or key == "retry_identity" and value not in ("stable", "attempt") or key == "event_order" and value not in ("version", "arrival")):
                    raise ValueError("Invalid active configuration")
            self.settings.update(target)
            self.save_config()
            return {"active": dict(self.settings)}
        if command == "provider":
            ids = [r["order_id"] for r in self.rows("SELECT order_id FROM orders ORDER BY order_id")] if target == "all" else self.ids(target, "orders", "order_id")
            status, result = self.http("/objects", {"order_ids": ids})
            for oid in ids:
                self.connection.execute("DELETE FROM snapshots WHERE order_id=?", (oid,))
            for obj in result["operations"]:
                self.connection.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(obj[k] for k in ("operation_id", "order_id", "kind", "amount_cents", "key", "parent_id", "status", "version", "created_tick", "settle_at")))
            return result
        if command == "cancel":
            if not isinstance(target, list) or not 1 <= len(target) <= 32 or any(not isinstance(x, str) for x in target):
                raise ValueError("cancel takes 1..32 operation_id strings; each result is independent")
            return {"results": [{"operation_id": opid, "status": status, "result": result} for opid in target for status, result in [self.http("/cancel", {"operation_id": opid})]]}
        if command == "fund":
            if type(target) is not int or not 1 <= target <= 100000:
                raise ValueError("fund takes a positive integer number of cents")
            status, result = self.http("/fund", {"amount_cents": target})
            return {"http_status": status, **result}
        if command == "refund":
            if not isinstance(target, list) or not 1 <= len(target) <= 32:
                raise ValueError("refund takes 1..32 {charge_id,amount_cents,key} objects")
            for row in target:
                if (not isinstance(row, dict) or set(row) != {"charge_id", "amount_cents", "key"} or not isinstance(row["charge_id"], str)
                        or type(row["amount_cents"]) is not int or not 1 <= row["amount_cents"] <= 100000
                        or not isinstance(row["key"], str) or not 1 <= len(row["key"]) <= 120):
                    raise ValueError("Invalid refund request")
            results = []
            for row in target:
                # Require a public snapshot to bind the order; do not consult
                # private provider state to supply an answer the operator lacks.
                obj = self.connection.execute("SELECT order_id FROM snapshots WHERE operation_id=?", (row["charge_id"],)).fetchone()
                if not obj:
                    results.append({"http_status": 409, "error": "retrieve the referenced charge with provider first"})
                    continue
                status, result = self.http("/refund", {"order_id": obj[0], "amount_cents": row["amount_cents"], "key": row["key"], "parent_id": row["charge_id"]})
                results.append({"http_status": status, **result})
            return {"results": results}
        if command == "adjust":
            if (not isinstance(target, dict) or set(target) != {"order_id", "delta_cents", "key"}
                    or not isinstance(target["order_id"], str) or type(target["delta_cents"]) is not int or not -100000 <= target["delta_cents"] <= 100000
                    or not isinstance(target["key"], str) or not 1 <= len(target["key"]) <= 120):
                raise ValueError("adjust takes {order_id,delta_cents,key}; affects local books only")
            self.ids([target["order_id"]], "orders", "order_id")
            old = self.connection.execute("SELECT order_id,delta_cents FROM adjustments WHERE key=?", (target["key"],)).fetchone()
            if old and tuple(old) != (target["order_id"], target["delta_cents"]):
                raise ValueError("local adjustment idempotency conflict")
            self.connection.execute("INSERT OR IGNORE INTO adjustments(order_id,delta_cents,key) VALUES (?,?,?)", (target["order_id"], target["delta_cents"], target["key"]))
            return {"local_adjustment_recorded": True, "external_effect": False}
        if command == "workload":
            if type(target) is not int or not 1 <= target <= 4:
                raise ValueError("workload takes an integer 1..4")
            start = self.connection.execute("SELECT count(*) FROM orders WHERE is_probe=1").fetchone()[0]
            if start + target > 16:
                raise ValueError("At most 16 probe orders")
            ids = []
            for n in range(start + 1, start + target + 1):
                oid = "probe-" + str(n)
                self.add_order(oid, 300 + 17 * n, True)
                ids.append(oid)
            return {"accepted": ids}
        if command == "wait" and target is None:
            return {"waiting_one_tick": True}
        if command == "verify" and target is None:
            from .settlement import healthy
            audit = self.audit()
            return {"passed": healthy(audit), **audit}
        if command == "finish" and target is None:
            return {"handover": True}
        raise ValueError("Unknown action or target; consult the public action contract")

    def call(self, action):
        try:
            if not isinstance(action, dict) or set(action) - {"command", "target"}:
                raise ValueError("Use command and optional target")
            result = self.operate(action.get("command"), action.get("target"))
            self.connection.commit()
        except (ValueError, TypeError, sqlite3.Error) as exc:
            self.connection.rollback()
            result = {"error": str(exc)[:300]}
        stable = isinstance(action, dict) and action.get("command") in ("verify", "finish") and "error" not in result
        if not stable:
            self.advance()
        # Public observation time is explicit: results are before the tick;
        # current_tick identifies the post-action boundary for the next action.
        result["current_tick"] = self.tick
        return {"result": result, "audit": self.audit(), "state_sha256": digest(self.tables()),
                "http_requests": self.http_requests, "tick": self.tick}

    def close(self):
        if not self.closed:
            self.provider.close()
        super().close()
