"""Public SQL interfaces and broken deployment for coupled refund recovery."""
from .reconciliation_sql import transform

INTERFACES = {
    "decode": {"input": "receipts", "columns": ("receipt", "event_type", "body"),
               "output": ("receipt", "operation_id", "order_id", "amount_cents", "status", "version"),
               "text_fields": ("operation_id", "order_id", "status")},
    "project": {"input": "decoded", "columns": ("receipt", "operation_id", "order_id", "amount_cents", "status", "version"),
                "output": ("operation_id", "order_id", "amount_cents", "status", "version"),
                "text_fields": ("operation_id", "order_id", "status")},
    "dispatch": {"input": "queue", "columns": ("intent_id", "order_id", "charge_id", "amount_cents", "charge_cents", "request_key", "attempt"),
                 "output": ("intent_id", "order_id", "charge_id", "amount_cents", "key"),
                 "text_fields": ("intent_id", "order_id", "charge_id", "key")},
}

BROKEN = {
    "decode": "SELECT receipt,json_extract(body,'$.operation_id') AS operation_id,json_extract(body,'$.order_id') AS order_id,json_extract(body,'$.charge_cents') AS amount_cents,json_extract(body,'$.status') AS status,json_extract(body,'$.version') AS version FROM receipts WHERE event_type='refund.updated'",
    "project": "SELECT operation_id,order_id,amount_cents,status,version FROM (SELECT *,row_number() OVER (PARTITION BY order_id ORDER BY receipt DESC) AS n FROM decoded) WHERE n=1",
    "dispatch": "SELECT intent_id,order_id,charge_id,amount_cents,request_key || '/attempt-' || attempt AS key FROM queue",
}


def run(sql, stage, rows):
    return transform(sql, stage, rows, interface=INTERFACES[stage])
