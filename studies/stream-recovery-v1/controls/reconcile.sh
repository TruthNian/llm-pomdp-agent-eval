set -euo pipefail
python3 - <<'PY'
import subprocess
for name in ('api','dispatch','connect'):
    subprocess.run(['supervisorctl','stop',name],check=False)
    value=subprocess.run(['supervisorctl','status',name],capture_output=True,text=True)
    print(value.stdout.strip())
    assert value.stdout.split()[1] in ('STOPPED','EXITED','FATAL'), value.stdout
PY
install -d -m 700 /var/backups/reconciliation
pg_dump -h 127.0.0.1 -p 5433 -U postgres -Fc commerce > /var/backups/reconciliation/current.dump
pg_dump -h 127.0.0.1 -p 5440 -U postgres -Fc commerce > /var/backups/reconciliation/salvaged.dump
cp -p /var/lib/commerce-dispatch.sqlite /var/backups/reconciliation/dispatch.sqlite
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

# Persist receipt identity by the business event, preserving already committed work.
path=Path('/srv/commerce/service.py')
text=path.read_text()
start=text.index('def dispatch():')
end=text.index('\n\nclass Carrier',start)
replacement='''def dispatch():
    from kafka import KafkaConsumer
    settings = config()
    ledger = sqlite3.connect('/var/lib/commerce-dispatch.sqlite')
    ledger.execute('CREATE TABLE IF NOT EXISTS event_receipts(event_id text PRIMARY KEY,reference text NOT NULL,booking_id text NOT NULL)')
    ledger.commit()
    consumer = KafkaConsumer(settings['topic'],bootstrap_servers='127.0.0.1:9092',
                             group_id=settings['group'],enable_auto_commit=False,
                             auto_offset_reset='earliest',max_poll_records=1,
                             value_deserializer=lambda raw:json.loads(raw) if raw else None)
    for message in consumer:
        event = message.value.get('after') if message.value else None
        if not event or event.get('kind') != 'release':
            consumer.commit()
            continue
        if ledger.execute('SELECT booking_id FROM event_receipts WHERE event_id=?',(event['event_id'],)).fetchone():
            consumer.commit()
            continue
        payload = event['payload']
        if isinstance(payload,str):
            payload = json.loads(payload)
        body = {k:payload[k] for k in ('customer','address','items')}
        body.update(client_reference=event['event_id'],order_reference=event['reference'])
        while True:
            try:
                status,found = http(settings['carrier']+'/bookings?client_reference='+urllib.parse.quote(event['event_id']))
                if status != 200:
                    raise ValueError('carrier lookup failed')
                values = found['bookings']
                if values:
                    if len(values)!=1 or any(values[0].get(k)!=v for k,v in body.items()):
                        raise ValueError('conflicting existing consignment')
                    receipt = values[0]
                else:
                    status,receipt = http(settings['carrier']+'/bookings',body,{'Idempotency-Key':'dispatch:'+event['event_id']})
                    if status not in (200,201):
                        raise ValueError('carrier rejected booking')
                break
            except (OSError,ValueError):
                logging.exception('dispatch pending for %s',event['event_id'])
                time.sleep(5)
        with ledger:
            ledger.execute('INSERT INTO event_receipts VALUES(?,?,?)',(event['event_id'],event['reference'],receipt['booking_id']))
        consumer.commit()
        logging.info('dispatched %s (%s): %s',event['reference'],event['event_id'],receipt['booking_id'])
'''
mode=os.environ.get('STREAM_CONTROL_MODE','preserve')
if mode=='blind_replay':
    replacement=replacement.replace("status,found = http(settings['carrier']+'/bookings?client_reference='+urllib.parse.quote(event['event_id']))",
                                    "status,found = 200, {'bookings': []}")
elif mode not in ('preserve','tables_only'):
    raise ValueError('Unknown artifact control')
if mode!='tables_only':
    path.write_text(text[:start]+replacement+text[end:])
settings=Path('/etc/commerce/application.json')
value=json.loads(settings.read_text())
value.update(port=5433,topic='commerce-recovery.public.outbox',group='commerce-recovery-dispatch')
settings.write_text(json.dumps(value)+'\n')
PY
supervisorctl start connect
python3 - <<'PY'
import json,time,urllib.request,urllib.error
from pathlib import Path
base='http://127.0.0.1:8083'
for _ in range(50):
    try:
        with urllib.request.urlopen(base+'/',timeout=2) as response:
            assert response.status==200
        break
    except (OSError,AssertionError): time.sleep(1)
else: raise RuntimeError('Connect did not start')
try:
    with urllib.request.urlopen(urllib.request.Request(base+'/connectors/commerce-outbox',method='DELETE'),timeout=10): pass
except urllib.error.HTTPError as error:
    if error.code!=404: raise
value=json.loads(Path('/etc/commerce/connector.json').read_text())
value['name']='commerce-recovery'
value['config'].update({'database.port':'5433','slot.name':'commerce_recovery','topic.prefix':'commerce-recovery'})
request=urllib.request.Request(base+'/connectors',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=10) as response: print(response.status,response.read().decode())
PY
supervisorctl start api dispatch
