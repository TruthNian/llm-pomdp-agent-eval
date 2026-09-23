set -euo pipefail
supervisorctl stop api
python3 - <<'PY'
import json,os
from pathlib import Path
import psycopg2
from psycopg2.extras import Json, RealDictCursor

source=psycopg2.connect(host='127.0.0.1',port=5440,user='postgres',dbname='commerce')
target=psycopg2.connect(host='127.0.0.1',port=5433,user='postgres',dbname='commerce')
with source, source.cursor(cursor_factory=RealDictCursor) as q:
    tables={}
    for table in ('orders','outbox','requests'):
        q.execute('SELECT * FROM '+table)
        tables[table]=[dict(row) for row in q]
with target, target.cursor(cursor_factory=RealDictCursor) as q:
    q.execute('LOCK TABLE orders,outbox,requests IN EXCLUSIVE MODE')
    q.execute('SELECT * FROM orders')
    current={row['reference']:dict(row) for row in q}
    for row in tables['orders']:
        old=current.get(row['reference'])
        fields=('reference','revision','customer','address','items','status')
        if old and old['revision']==row['revision']:
            assert all(old[k]==row[k] for k in fields), 'Conflicting accepted revision'
        if old and old['revision']>=row['revision']:
            continue
        q.execute('''INSERT INTO orders(reference,revision,customer,address,items,status,updated_at)
                     VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(reference) DO UPDATE SET
                     revision=EXCLUDED.revision,customer=EXCLUDED.customer,address=EXCLUDED.address,
                     items=EXCLUDED.items,status=EXCLUDED.status,updated_at=EXCLUDED.updated_at''',
                  (row['reference'],row['revision'],row['customer'],row['address'],Json(row['items']),row['status'],row['updated_at']))
    for row in tables['outbox']:
        q.execute('''INSERT INTO outbox(event_id,reference,revision,kind,payload,created_at)
                     VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(event_id) DO NOTHING''',
                  (row['event_id'],row['reference'],row['revision'],row['kind'],Json(row['payload']),row['created_at']))
    for row in tables['requests']:
        q.execute('''INSERT INTO requests(request_id,body,response,accepted_at) VALUES(%s,%s,%s,%s)
                     ON CONFLICT(request_id) DO NOTHING''',
                  (row['request_id'],Json(row['body']),Json(row['response']),row['accepted_at']))
    q.execute('SELECT count(*) AS orders,(SELECT count(*) FROM outbox) AS events,(SELECT count(*) FROM requests) AS requests FROM orders')
    print(dict(q.fetchone()))
source.close(); target.close()

PY
supervisorctl start api
