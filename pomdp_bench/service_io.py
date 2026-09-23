"""Shared bounded HTTP/SQLite plumbing; no task-specific transitions."""
from contextlib import closing
import http.client
import json
import sqlite3


class ServiceIO:
    def rows(self, sql, values=()):
        return [dict(r) for r in self.connection.execute(sql, values)]

    def http(self, path, body):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request("POST", path, json.dumps(body), {"Content-Type": "application/json"})
            response = connection.getresponse()
            result = json.loads(response.read())
            self.http_requests += 1
            return response.status, result
        finally:
            connection.close()

    def query(self, sql):
        if not isinstance(sql, str) or not 1 <= len(sql) <= 6000:
            raise ValueError("query requires 1-6000 characters")
        with closing(sqlite3.connect(self.db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
            con.row_factory = sqlite3.Row
            con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 262144)
            con.execute("PRAGMA query_only=ON")
            allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
            con.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
            progress = [0]
            def interrupt():
                progress[0] += 1
                return progress[0] > 1000
            con.set_progress_handler(interrupt, 1000)
            cursor = con.execute(sql)
            rows = cursor.fetchmany(101)
            return {"columns": [c[0] for c in cursor.description],
                    "rows": [[{"hex": v.hex()} if isinstance(v, bytes) else v for v in r] for r in rows[:100]],
                    "truncated": len(rows) > 100}

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.connection.close()
        self.temp.cleanup()
