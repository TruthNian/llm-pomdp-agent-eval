"""Order API. Runtime configuration is read for each request."""
import json
import logging
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent


@contextmanager
def connection(role):
    config = json.loads((ROOT / "config.json").read_text())
    conn = psycopg2.connect(dbname="orders", user="orders", host="127.0.0.1",
                           port=config[role + "_port"], connect_timeout=5)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def get_order(cursor, reference):
    cursor.execute("SELECT id,reference,customer,address FROM orders WHERE reference=%s", (reference,))
    row = cursor.fetchone()
    if row is None:
        return None
    cursor.execute("SELECT sku,quantity,unit_cents FROM lines WHERE order_id=%s ORDER BY line_no", (row["id"],))
    return {"order_id": row["id"], "reference": row["reference"], "customer": row["customer"],
            "address": row["address"], "items": [dict(item) for item in cursor.fetchall()]}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self.reply(200, {"status": "up"})
            return
        if not path.startswith("/orders/"):
            self.reply(404, {"error": "not found"})
            return
        try:
            with connection("read") as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
                result = get_order(cursor, unquote(path.removeprefix("/orders/")))
            self.reply(200 if result else 404, result or {"error": "order not found"})
        except psycopg2.Error:
            logging.exception("order read failed")
            self.reply(503, {"error": "temporarily unavailable"})

    def do_POST(self):
        if urlsplit(self.path).path != "/orders":
            self.reply(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("body size")
            body = json.loads(self.rfile.read(length))
            if set(body) != {"reference", "customer", "address", "items"}:
                raise ValueError("fields")
            if any(not isinstance(body[k], str) or not body[k] for k in ("reference", "customer", "address")):
                raise ValueError("identity")
            if not isinstance(body["items"], list) or not 1 <= len(body["items"]) <= 20:
                raise ValueError("items")
            for item in body["items"]:
                if (set(item) != {"sku", "quantity", "unit_cents"} or not isinstance(item["sku"], str)
                        or not item["sku"] or type(item["quantity"]) is not int or item["quantity"] <= 0
                        or type(item["unit_cents"]) is not int or item["unit_cents"] < 0):
                    raise ValueError("line")
        except (ValueError, TypeError, KeyError):
            self.reply(400, {"error": "invalid order"})
            return
        try:
            with connection("write") as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Serialize retries of the same business reference without global serialization.
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (body["reference"],))
                existing = get_order(cursor, body["reference"])
                if existing:
                    if {k: v for k, v in existing.items() if k != "order_id"} != body:
                        self.reply(409, {"error": "reference already used"})
                        return
                    result, status = existing, 200
                else:
                    cursor.execute("INSERT INTO orders(reference,customer,address) VALUES(%s,%s,%s) RETURNING id",
                                   (body["reference"], body["customer"], body["address"]))
                    order_id = cursor.fetchone()["id"]
                    for number, item in enumerate(body["items"]):
                        cursor.execute("INSERT INTO lines(order_id,line_no,sku,quantity,unit_cents) VALUES(%s,%s,%s,%s,%s)",
                                       (order_id, number, item["sku"], item["quantity"], item["unit_cents"]))
                    result, status = {"order_id": order_id, **body}, 201
            self.reply(status, result)
        except psycopg2.Error:
            logging.exception("order write failed")
            self.reply(503, {"error": "temporarily unavailable"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
