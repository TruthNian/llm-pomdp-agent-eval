"""Actual SQL component repair with delayed HTTP input and independent business truth."""
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading

from .generator import digest
from .reconciliation_data import BROKEN, CONTRACTS, SHAPES, STAGES, batch
from .reconciliation_sql import pipeline
from .service_io import ServiceIO

DOCS = {
    "operations": "Repair the deployed three-component reconciliation pipeline, recover historical output, exercise two new workload batches, and hand over. "
        "The provider's current positions are authoritative. Its notification feed is delayed, duplicated and out of order. "
        "Reads and rejected actions advance one tick. Each tick imports available HTTP feed receipts; output is NOT automatically rebuilt. "
        "There is no config switch implementing a repair. Read contract, source and schema; patch actual SQL; test/deploy/refresh deliberately.",
    "schema": "Local SQL tables: receipts(receipt INTEGER,body TEXT); normalized(receipt,merchant,object,currency,epoch,revision,amount_minor); "
        "positions(merchant,object,currency,amount_minor); report(merchant,currency,net_minor); components(stage,active,staged); "
        "meta(key,value). These materialized outputs change only on refresh. query is read-only, maximum 100 rows. "
        "The provider database, future feed and authoritative positions are NOT in this connection.",
    "pipeline": "normalize SELECT reads ONLY receipts and outputs receipt,merchant,object,currency,epoch,revision,amount_minor. "
        "resolve SELECT reads ONLY normalized and outputs merchant,object,currency,amount_minor. "
        "aggregate SELECT reads ONLY positions and outputs merchant,currency,net_minor. Column names/order are exact. "
        "Stages run in separate in-memory SQLite databases containing only their public input. "
        "SQL supports CTEs, joins, grouping, window functions, JSON extraction and exact minor(value,currency,unit). "
        "No DDL/DML, ATTACH, extensions, random/clock functions, files or provider/oracle access. "
        "Numbers must be integers; currency/merchant/object nonempty strings. Limits: 6000 SQL chars/stage,256 output rows,1000000 VM instructions. "
        "patch changes one staged source only. test runs the whole staged pipeline against currently received data, returning actual intermediate output; "
        "it is not an oracle and does not change production. deploy validates then atomically activates all staged SQL without rebuilding old output. "
        "refresh atomically replaces all materialized outputs using active SQL and current receipts; failures preserve the previous output. "
        "A successful SQL execution does not establish business correctness. No source-string matching is used for acceptance.",
    "timing": "80 actions including finish. Each normal action runs BEFORE advancing one tick and importing all newly available feed receipts. "
        "Payload delay is at most 8 ticks after a workload. No wall-clock-dependent changes. work is bounded to three extra batches; at least two required. "
        "verify/finish are read-only stable boundaries (no tick, traffic or processing); invalid calls still advance. "
        "Wait for pending deliveries, then refresh; query/provider/test/deploy never repair stored output. "
        "Every action other than valid verify/finish expires a PASS, including reads. Provider queries return state at that call.",
}


class Runtime(ServiceIO):
    def __init__(self, case):
        self.case, self.tick, self.probes, self.http_requests, self.closed = case, 0, 0, 0, False
        self.temp = tempfile.TemporaryDirectory(prefix="reconciliation-")
        self.db = Path(self.temp.name) / "local.sqlite"
        self.connection = sqlite3.connect(self.db)
        self.connection.row_factory = sqlite3.Row
        self.provider = sqlite3.connect(Path(self.temp.name) / "provider.sqlite", check_same_thread=False)
        self.provider.row_factory = sqlite3.Row
        self.connection.executescript("CREATE TABLE receipts(receipt INTEGER PRIMARY KEY,body TEXT);"
            "CREATE TABLE components(stage TEXT PRIMARY KEY,active TEXT,staged TEXT);"
            "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);")
        for stage, table in (("normalize", "normalized"), ("resolve", "positions"), ("aggregate", "report")):
            self.connection.execute(f"CREATE TABLE {table} ({','.join(SHAPES[stage])})")
        self.provider.executescript("CREATE TABLE feed(receipt INTEGER PRIMARY KEY,due INTEGER,body TEXT);"
            "CREATE TABLE truth(merchant TEXT,object TEXT,currency TEXT,amount_minor INTEGER,PRIMARY KEY(merchant,object));")
        for stage, sql in BROKEN[case["profile"]].items():
            self.connection.execute("INSERT INTO components VALUES (?,?,?)", (stage, sql, sql))
        self.lock = threading.RLock()
        runtime = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                with runtime.lock:
                    if self.path == "/feed":
                        body = {"receipts": runtime.prows("SELECT receipt,body FROM feed WHERE due<=? ORDER BY receipt", (runtime.tick,))}
                    elif self.path == "/positions":
                        body = {"positions": runtime.prows("SELECT * FROM truth ORDER BY merchant,object"), "at_tick": runtime.tick}
                    else:
                        self.send_error(404)
                        return
                encoded = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.seed_batch(0, -4)
        self.ingest()
        self.refresh()
        self.save_meta()

    def prows(self, sql, values=()):
        return [dict(r) for r in self.provider.execute(sql, values)]

    def seed_batch(self, number, base):
        payloads, truth = batch(self.case["profile"], number)
        for delay, body in payloads:
            self.provider.execute("INSERT INTO feed(due,body) VALUES (?,?)", (base+delay, body))
        self.provider.executemany("INSERT INTO truth VALUES (?,?,?,?)", truth)
        self.provider.commit()

    def ingest(self):
        _, result = self.http("/feed", {})
        self.connection.executemany("INSERT OR IGNORE INTO receipts VALUES (?,?)", [(r["receipt"], r["body"]) for r in result["receipts"]])
        self.connection.commit()

    def sources(self, column):
        return {r["stage"]: r[column] for r in self.rows("SELECT * FROM components")}

    def receipt_rows(self):
        return [list(r) for r in self.connection.execute("SELECT receipt,body FROM receipts ORDER BY receipt")]

    def refresh(self):
        outputs = pipeline(self.sources("active"), self.receipt_rows())
        with self.connection:
            for stage, table in (("normalize", "normalized"), ("resolve", "positions"), ("aggregate", "report")):
                self.connection.execute(f"DELETE FROM {table}")
                self.connection.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in SHAPES[stage])})", outputs[stage])
            self.connection.execute("INSERT OR REPLACE INTO meta VALUES ('materialized',?)", (self.input_digest(),))
        return {stage: len(rows) for stage, rows in outputs.items()}

    def input_digest(self):
        return digest([self.sources("active"), self.receipt_rows()])

    def save_meta(self):
        for key, value in (("tick", self.tick), ("probes", self.probes)):
            self.connection.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))
        self.connection.commit()

    def audit(self):
        expected = [tuple(r) for r in self.provider.execute("SELECT merchant,object,currency,amount_minor FROM truth")]
        actual = [tuple(r) for r in self.connection.execute("SELECT * FROM positions")]
        totals = {}
        for merchant, _, currency, amount in expected:
            totals[merchant, currency] = totals.get((merchant, currency), 0) + amount
        expected_report = Counter((merchant, currency, amount) for (merchant, currency), amount in totals.items())
        actual_report = Counter(tuple(r) for r in self.connection.execute("SELECT * FROM report"))
        materialized = self.connection.execute("SELECT value FROM meta WHERE key='materialized'").fetchone()
        return {"position_errors": sum((Counter(expected)-Counter(actual)).values()) + sum((Counter(actual)-Counter(expected)).values()),
                "report_errors": sum((expected_report-actual_report).values()) + sum((actual_report-expected_report).values()),
                "pending_receipts": self.provider.execute("SELECT count(*) FROM feed WHERE due>?", (self.tick,)).fetchone()[0],
                "output_current": bool(materialized and materialized[0] == self.input_digest()), "workload_batches": self.probes,
                "receipt_count": len(self.receipt_rows()), "business_objects": len(expected)}

    def tables(self):
        return {"local": {table: self.rows(f"SELECT * FROM {table} ORDER BY 1,2") for table in ("receipts", "normalized", "positions", "report", "components", "meta")},
                "provider": {table: self.prows(f"SELECT * FROM {table} ORDER BY 1,2") for table in ("feed", "truth")}}

    def operate(self, command, target):
        if command == "inspect":
            if target in DOCS:
                return {"text": DOCS[target]}
            if target == "contract":
                return {"text": CONTRACTS[self.case["profile"]]}
            if target == "source":
                return {"components": self.rows("SELECT * FROM components ORDER BY stage")}
            if target == "metrics":
                audit = self.audit()
                return {k: audit[k] for k in ("pending_receipts", "output_current", "workload_batches", "receipt_count")}
            raise ValueError("inspect operations,contract,schema,pipeline,timing,source,metrics")
        if command == "query":
            return self.query(target)
        if command == "provider" and target == "all":
            return self.http("/positions", {})[1]
        if command == "patch":
            if (not isinstance(target, dict) or set(target) != {"stage", "sql"} or target["stage"] not in STAGES
                    or not isinstance(target["sql"], str) or not 1 <= len(target["sql"]) <= 6000):
                raise ValueError("patch takes {stage:normalize|resolve|aggregate,sql:1..6000 characters}")
            self.connection.execute("UPDATE components SET staged=? WHERE stage=?", (target["sql"], target["stage"]))
            return {"staged": target["stage"], "deployed": False}
        if command in ("test", "deploy") and target is None:
            outputs = pipeline(self.sources("staged"), self.receipt_rows())
            if command == "test":
                return {"execution_ok": True, "business_correctness": "not established by execution", "outputs": outputs, "columns": {stage: list(columns) for stage, columns in SHAPES.items()}}
            self.connection.execute("UPDATE components SET active=staged")
            return {"deployed": True, "materialized_output_rebuilt": False}
        if command == "refresh" and target is None:
            return {"materialized_rows": self.refresh()}
        if command == "workload" and type(target) is int and target == 1:
            if self.probes >= 3:
                raise ValueError("At most three additional workload batches")
            self.probes += 1
            self.seed_batch(self.probes, self.tick)
            return {"submitted_batch": self.probes, "maximum_delivery_delay": 8}
        if command == "wait" and target is None:
            return {"waiting_one_tick": True}
        if command == "verify" and target is None:
            from .reconciliation import healthy
            audit = self.audit()
            return {"passed": healthy(audit), **audit}
        if command == "finish" and target is None:
            return {"handover": True}
        raise ValueError("Unknown action/target; consult the public contract")

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
            self.tick += 1
            self.ingest()
            self.save_meta()
        result["current_tick"] = self.tick
        return {"result": result, "audit": self.audit(), "state_sha256": digest(self.tables()),
                "http_requests": self.http_requests, "tick": self.tick}

    def close(self):
        if not self.closed:
            self.provider.close()
        super().close()
