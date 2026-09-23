"""Bounded SQL transformations over copied public inputs, without host access."""
from contextlib import closing
from decimal import Decimal, InvalidOperation
import sqlite3

from .reconciliation_data import INPUTS, SHAPES, STAGES


def minor(value, currency, unit):
    if currency not in ("USD", "JPY", "KWD") or unit not in ("minor", "major"):
        raise ValueError("Unknown currency or unit")
    try:
        amount = Decimal(str(value))
        amount *= 10 ** ({"USD": 2, "JPY": 0, "KWD": 3}[currency] if unit == "major" else 0)
        if not amount.is_finite() or amount != amount.to_integral_value() or abs(amount) > 10**12:
            raise ValueError("Money must be exact bounded integer minor units")
        return int(amount)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal amount") from exc


def transform(sql, stage, rows, *, interface=None):
    if not isinstance(sql, str) or not 1 <= len(sql) <= 6000:
        raise ValueError("SQL must contain 1..6000 characters")
    columns = interface["columns"] if interface is not None else (("receipt", "body") if stage == "normalize" else SHAPES[STAGES[STAGES.index(stage)-1]])
    table = INPUTS[stage] if interface is None else interface["input"]
    shape = SHAPES[stage] if interface is None else interface["output"]
    text_fields = {"merchant", "object", "currency"} if interface is None else set(interface["text_fields"])
    with closing(sqlite3.connect(":memory:")) as con:
        # Only the previous component's PUBLIC rows enter this database. There
        # is no connection/ATTACH path to the provider, host, oracle or secrets.
        con.execute(f"CREATE TABLE {table} ({','.join(columns)})")
        con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})", rows)
        con.create_function("minor", 3, minor, deterministic=True)
        con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
        con.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 6000)
        con.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 32)
        con.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 50)
        con.execute("PRAGMA query_only=ON")
        functions = {"json_extract", "coalesce", "ifnull", "nullif", "iif", "abs", "round", "sum", "total",
                     "count", "min", "max", "avg", "row_number", "rank", "dense_rank", "first_value", "last_value",
                     "lag", "lead", "length", "substr", "substring", "lower", "upper", "trim", "typeof", "minor"}

        def authorize(action, arg1, arg2, *_):
            if action == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK if arg1 == table else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION:
                return sqlite3.SQLITE_OK if (arg2 or "").lower() in functions else sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE) else sqlite3.SQLITE_DENY

        con.set_authorizer(authorize)
        work = [0]

        def interrupt():
            work[0] += 1
            return work[0] > 1000

        con.set_progress_handler(interrupt, 1000)
        cursor = con.execute(sql)
        if tuple(c[0] for c in cursor.description or ()) != shape:
            raise ValueError(f"{stage} output columns must be {shape}")
        result = [list(r) for r in cursor.fetchmany(257)]
        if len(result) > 256:
            raise ValueError("Component output exceeds 256 rows")
        for row in result:
            for column, value in zip(shape, row):
                if column in text_fields:
                    if not isinstance(value, str) or not 1 <= len(value) <= 120:
                        raise ValueError(f"{column} must be a nonempty bounded string")
                elif type(value) is not int or abs(value) > 10**12:
                    raise ValueError(f"{column} must be a bounded integer")
        return sorted(result)


def pipeline(sources, receipts):
    output, rows = {}, receipts
    for stage in STAGES:
        try:
            rows = transform(sources[stage], stage, rows)
        except (ValueError, sqlite3.Error) as exc:
            raise ValueError(f"{stage}: {exc}") from exc
        output[stage] = rows
    return output
