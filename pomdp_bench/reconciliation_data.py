"""Constructed payment feeds. Business truth is supplied independently of SQL rules.

These are two development contracts, not independently sampled production incidents.
No fixture ID or reference patch is included in the operator observation.
"""
import json

PROFILES = ("capture_snapshots", "posting_corrections")
STAGES = ("normalize", "resolve", "aggregate")
SHAPES = {
    "normalize": ("receipt", "merchant", "object", "currency", "epoch", "revision", "amount_minor"),
    "resolve": ("merchant", "object", "currency", "amount_minor"),
    "aggregate": ("merchant", "currency", "net_minor"),
}
INPUTS = {"normalize": "receipts", "resolve": "normalized", "aggregate": "positions"}

CONTRACTS = {
    "capture_snapshots": "The upstream feed contains FULL CAPTURE SNAPSHOTS, not deltas. "
        "A capture is identified by (merchant, capture_id); capture IDs are only merchant-local. "
        "Within a capture choose greatest (generation, revision), lexicographically: revision resets on generation change. "
        "received order and sent_at are not business revision order. Equal business versions are exact duplicate payloads. "
        "Wire schema 1: merchant,capture_id,currency,generation,revision,captured,refunded; captured/refunded are integer minor units. "
        "Wire schema 2: merchant,capture_id,currency,generation,revision,money:{captured,refunded}; amounts are decimal major-unit STRINGS. "
        "Net per capture is captured minus refunded. Preserve zero-net captures. Sum distinct current captures per merchant AND currency. "
        "Both schemas coexist. Currency exponents: USD=2, JPY=0, KWD=3. The public minor(value,currency,unit) SQL function "
        "converts exactly; unit is minor or major. Never sum snapshot revisions or combine currencies.",
    "posting_corrections": "The upstream feed contains CORRECTABLE POSTINGS. "
        "A posting is identified by (account, entry_id); entry IDs are only account-local. "
        "invoice_id groups multiple distinct charges/refunds and is NOT a posting identity. "
        "Each revision REPLACES the amount/status of that entry; retain greatest revision per account and entry. "
        "delivery order and sent_at are not revision order. Equal revisions are exact duplicate payloads. "
        "Fields: account,entry_id,invoice_id,currency,revision,kind(charge|refund),status(posted|pending|void),amount,unit(minor|major). "
        "amount is unsigned: posted charges contribute positive, posted refunds negative; pending/void contribute zero. "
        "Preserve zero-value entries. Sum distinct current entries per account AND currency. "
        "The normalized merchant is account, object is entry_id, epoch is 0. Currency exponents: USD=2, JPY=0, KWD=3. "
        "minor(value,currency,unit) converts exactly. A refund is a separate entry, never an overwrite of its invoice's charge.",
}

BROKEN = {
    "capture_snapshots": {
        "normalize": "SELECT receipt,json_extract(body,'$.merchant') AS merchant,json_extract(body,'$.capture_id') AS object,json_extract(body,'$.currency') AS currency,json_extract(body,'$.generation') AS epoch,json_extract(body,'$.revision') AS revision,coalesce(json_extract(body,'$.captured'),0)-coalesce(json_extract(body,'$.refunded'),0) AS amount_minor FROM receipts",
        "resolve": "SELECT merchant,object,currency,amount_minor FROM (SELECT *,row_number() OVER (PARTITION BY object ORDER BY revision DESC,receipt DESC) AS n FROM normalized) WHERE n=1",
        "aggregate": "SELECT merchant,currency,sum(amount_minor) AS net_minor FROM positions GROUP BY merchant,currency",
    },
    "posting_corrections": {
        "normalize": "SELECT receipt,json_extract(body,'$.account') AS merchant,json_extract(body,'$.invoice_id') AS object,json_extract(body,'$.currency') AS currency,0 AS epoch,json_extract(body,'$.revision') AS revision,minor(json_extract(body,'$.amount'),json_extract(body,'$.currency'),json_extract(body,'$.unit')) AS amount_minor FROM receipts",
        "resolve": "SELECT merchant,object,currency,sum(amount_minor) AS amount_minor FROM normalized GROUP BY merchant,object,currency",
        "aggregate": "SELECT merchant,currency,sum(amount_minor) AS net_minor FROM positions WHERE amount_minor>0 GROUP BY merchant,currency",
    },
}


def batch(profile, number):
    """Return (delayed public payloads, authoritative final positions).

    Expected amounts are explicit integer business facts, never calculated by a
    candidate/reference SQL decoder. Repeated batches are probes, not new tasks.
    """
    payloads, truth = [], []
    suffix = str(number)

    def snapshot(merchant, obj, currency, epoch, revision, captured, refunded, schema, delay):
        row = dict(merchant=merchant, capture_id=obj, currency=currency,
                   generation=epoch, revision=revision, schema=schema, sent_at=100-delay)
        if schema == 1:
            row.update(captured=captured, refunded=refunded)
        else:
            row["money"] = dict(captured=captured, refunded=refunded)
        payloads.append((delay, json.dumps(row, sort_keys=True)))

    def posting(account, entry, invoice, currency, revision, kind, status, amount, unit, delay):
        row = dict(account=account, entry_id=entry, invoice_id=invoice, currency=currency,
                   revision=revision, kind=kind, status=status, amount=amount, unit=unit, sent_at=100-delay)
        payloads.append((delay, json.dumps(row, sort_keys=True)))

    if profile == "capture_snapshots":
        obj = "capture-" + suffix
        snapshot("east", obj, "USD", 1, 9, 1200+100*number, 200, 1, 1)
        snapshot("east", obj, "USD", 2, 1, f"{12+number}.00", "4.00", 2, 3)
        snapshot("east", obj, "USD", 1, 9, 1200+100*number, 200, 1, 8)
        snapshot("west", obj, "JPY", 1, 1, 900+number, 0, 1, 2)
        snapshot("east", "dinar-"+suffix, "KWD", 1, 3, "2.345", "0.345", 2, 4)
        snapshot("west", "zero-"+suffix, "USD", 1, 2, 500, 500, 1, 5)
        truth = [("east", obj, "USD", 800+100*number), ("west", obj, "JPY", 900+number),
                 ("east", "dinar-"+suffix, "KWD", 2000), ("west", "zero-"+suffix, "USD", 0)]
    elif profile == "posting_corrections":
        invoice, obj = "invoice-"+suffix, "entry-"+suffix
        posting("east", obj, invoice, "USD", 1, "charge", "posted", 700+100*number, "minor", 1)
        posting("east", obj, invoice, "USD", 2, "charge", "posted", f"{6+number}.50", "major", 3)
        posting("east", obj, invoice, "USD", 1, "charge", "posted", 700+100*number, "minor", 8)
        posting("east", "split-"+suffix, invoice, "USD", 1, "charge", "posted", 500, "minor", 2)
        posting("east", "refund-"+suffix, invoice, "USD", 1, "refund", "posted", "2.00", "major", 4)
        posting("west", obj, invoice, "JPY", 1, "charge", "posted", 900+number, "minor", 2)
        posting("east", "dinar-"+suffix, invoice, "KWD", 1, "charge", "posted", "1.234", "major", 2)
        posting("east", "dinar-refund-"+suffix, invoice, "KWD", 1, "refund", "posted", "0.234", "major", 5)
        posting("west", "void-"+suffix, invoice, "USD", 1, "charge", "pending", 300, "minor", 1)
        posting("west", "void-"+suffix, invoice, "USD", 2, "charge", "void", 300, "minor", 6)
        truth = [("east", obj, "USD", 650+100*number), ("east", "split-"+suffix, "USD", 500),
                 ("east", "refund-"+suffix, "USD", -200), ("west", obj, "JPY", 900+number),
                 ("east", "dinar-"+suffix, "KWD", 1234), ("east", "dinar-refund-"+suffix, "KWD", -234),
                 ("west", "void-"+suffix, "USD", 0)]
    else:
        raise ValueError("Unknown feed contract")
    # A second receipt for the same event is NOT another economic operation.
    payloads.append((7, payloads[1][1]))
    return payloads, truth
