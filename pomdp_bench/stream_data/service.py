"""Commerce API, outbox consumer and the local carrier implementation."""
import argparse
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2
from psycopg2.extras import Json, RealDictCursor

CONFIG = Path('/etc/commerce/application.json')


def config():
    return json.loads(CONFIG.read_text())


@contextmanager
def database():
    conn = psycopg2.connect(dbname='commerce', user='commerce', host='127.0.0.1',
                            port=config()['port'], connect_timeout=5)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def order(cursor, reference):
    cursor.execute('SELECT id,reference,revision,customer,address,items,status FROM orders WHERE reference=%s', (reference,))
    row = cursor.fetchone()
    return dict(row) if row else None


def command(body):
    kind = body.get('kind')
    required = {'request_id','reference','revision','kind'}
    if kind in ('draft','amend'):
        required |= {'customer','address','items'}
    if set(body) != required or kind not in ('draft','amend','release','cancel'):
        return 400, {'error':'invalid command fields'}
    try:
        uuid.UUID(body['request_id'])
    except (ValueError, TypeError, AttributeError):
        return 400, {'error':'request_id must be a UUID'}
    if (not isinstance(body['reference'],str) or not body['reference'] or
            type(body['revision']) is not int or body['revision'] < 1):
        return 400, {'error':'invalid reference or revision'}
    if kind in ('draft','amend'):
        if any(not isinstance(body[k],str) or not body[k] for k in ('customer','address')):
            return 400, {'error':'invalid customer or address'}
        items = body['items']
        if not isinstance(items,list) or not 1 <= len(items) <= 20:
            return 400, {'error':'invalid line items'}
        for item in items:
            if (not isinstance(item,dict) or set(item) != {'sku','quantity','unit_cents'}
                    or not isinstance(item['sku'],str) or not item['sku']
                    or type(item['quantity']) is not int or item['quantity'] <= 0
                    or type(item['unit_cents']) is not int or item['unit_cents'] < 0):
                return 400, {'error':'invalid line item'}
    with database() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(body['request_id'],))
        cursor.execute('SELECT body,response FROM requests WHERE request_id=%s',(body['request_id'],))
        previous = cursor.fetchone()
        if previous:
            return (200,previous['response']) if previous['body'] == body else (409,{'error':'request ID already used'})
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,1))',(body['reference'],))
        current = order(cursor,body['reference'])
        if kind == 'draft':
            if current:
                return 409, {'error':'order reference already exists'}
            cursor.execute('INSERT INTO orders(reference,revision,customer,address,items,status) VALUES(%s,%s,%s,%s,%s,%s)',
                           (body['reference'],body['revision'],body['customer'],body['address'],Json(body['items']),'draft'))
        else:
            if not current:
                return 404, {'error':'order not found'}
            if current['status'] != 'draft' or body['revision'] <= current['revision']:
                return 409, {'error':'order is final or revision is stale'}
            if kind == 'amend':
                cursor.execute('UPDATE orders SET customer=%s,address=%s,items=%s,revision=%s,updated_at=clock_timestamp() WHERE reference=%s',
                               (body['customer'],body['address'],Json(body['items']),body['revision'],body['reference']))
            else:
                cursor.execute('UPDATE orders SET status=%s,revision=%s,updated_at=clock_timestamp() WHERE reference=%s',
                               ('released' if kind == 'release' else 'cancelled',body['revision'],body['reference']))
        value = order(cursor,body['reference'])
        event_id = body['request_id']
        cursor.execute('INSERT INTO outbox(event_id,reference,revision,kind,payload) VALUES(%s,%s,%s,%s,%s)',
                       (event_id,body['reference'],body['revision'],kind,Json(value)))
        response = {'event_id':event_id,'order':value}
        cursor.execute('INSERT INTO requests(request_id,body,response) VALUES(%s,%s,%s)',
                       (body['request_id'],Json(body),Json(response)))
    return 201, response


class Handler(BaseHTTPRequestHandler):
    def reply(self,status,body):
        raw = json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        length = int(self.headers.get('Content-Length','0'))
        if not 0 < length <= 65536:
            raise ValueError('body length')
        value = json.loads(self.rfile.read(length))
        if not isinstance(value,dict):
            raise ValueError('body object')
        return value


class Api(Handler):
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == '/health':
            return self.reply(200,{'status':'up'})
        if not path.startswith('/orders/'):
            return self.reply(404,{'error':'not found'})
        try:
            with database() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
                result = order(cursor,urllib.parse.unquote(path.removeprefix('/orders/')))
            self.reply(200 if result else 404,result or {'error':'order not found'})
        except psycopg2.Error:
            logging.exception('order read failed')
            self.reply(503,{'error':'temporarily unavailable'})

    def do_POST(self):
        if self.path != '/commands':
            return self.reply(404,{'error':'not found'})
        try:
            body = self.body()
            status,result = command(body)
            logging.info('command %s %s %s -> %s',body.get('request_id'),body.get('reference'),body.get('kind'),status)
            self.reply(status,result)
        except (ValueError,TypeError):
            self.reply(400,{'error':'invalid JSON request'})
        except psycopg2.Error:
            logging.exception('command failed')
            self.reply(503,{'error':'temporarily unavailable'})


def http(url,body=None,headers=None):
    request = urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,
                                     headers={'Content-Type':'application/json',**(headers or {})})
    try:
        response = urllib.request.urlopen(request,timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status,json.load(response)


def dispatch():
    from kafka import KafkaConsumer
    settings = config()
    ledger = sqlite3.connect('/var/lib/commerce-dispatch.sqlite')
    ledger.execute('CREATE TABLE IF NOT EXISTS receipts(source_id integer PRIMARY KEY,event_id text NOT NULL,reference text NOT NULL,booking_id text NOT NULL)')
    ledger.commit()
    consumer = KafkaConsumer(settings['topic'],bootstrap_servers='127.0.0.1:9092',
                             group_id=settings['group'],enable_auto_commit=False,
                             auto_offset_reset='earliest',max_poll_records=1,
                             value_deserializer=lambda raw:json.loads(raw) if raw else None)
    for message in consumer:
        value = message.value
        event = value.get('after') if value else None
        if not event or event.get('kind') != 'release':
            consumer.commit()
            continue
        # One database outbox row represents one dispatch request.
        old = ledger.execute('SELECT booking_id FROM receipts WHERE source_id=?',(event['id'],)).fetchone()
        if old:
            logging.info('already dispatched source row %s: %s',event['id'],old[0])
            consumer.commit()
            continue
        payload = event['payload']
        if isinstance(payload,str):
            payload = json.loads(payload)
        body = {k:payload[k] for k in ('customer','address','items')}
        body.update(client_reference=event['event_id'],order_reference=event['reference'])
        while True:
            try:
                status,receipt = http(settings['carrier']+'/bookings',body,{'Idempotency-Key':'outbox:'+str(event['id'])})
                if status in (200,201):
                    break
                logging.error('carrier rejected outbox %s: HTTP %s %s',event['id'],status,receipt)
            except (OSError,ValueError):
                logging.exception('carrier request failed for outbox %s',event['id'])
            time.sleep(5)
        with ledger:
            ledger.execute('INSERT INTO receipts VALUES(?,?,?,?)',
                           (event['id'],event['event_id'],event['reference'],receipt['booking_id']))
        consumer.commit()
        logging.info('dispatched %s (%s): %s',event['reference'],event['event_id'],receipt['booking_id'])


class Carrier(Handler):
    path = Path('/data/carrier.sqlite')

    @classmethod
    def connect(cls):
        conn = sqlite3.connect(cls.path,timeout=10)
        conn.execute('PRAGMA busy_timeout=10000')
        conn.execute('CREATE TABLE IF NOT EXISTS bookings(id integer PRIMARY KEY,key text UNIQUE NOT NULL,body text NOT NULL,booking_id text UNIQUE NOT NULL,accepted_at real NOT NULL)')
        return conn

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/health':
            return self.reply(200,{'status':'up'})
        if parsed.path != '/bookings':
            return self.reply(404,{'error':'not found'})
        query = urllib.parse.parse_qs(parsed.query)
        conn = type(self).connect()
        try:
            rows = conn.execute('SELECT key,body,booking_id,accepted_at FROM bookings ORDER BY id').fetchall()
            values = [{**json.loads(body),'idempotency_key':key,'booking_id':bid,'accepted_at':at} for key,body,bid,at in rows]
            for field in ('client_reference','order_reference'):
                if field in query:
                    values = [v for v in values if v[field] == query[field][0]]
            self.reply(200,{'bookings':values})
        finally:
            conn.close()

    def do_POST(self):
        if self.path != '/bookings':
            return self.reply(404,{'error':'not found'})
        try:
            body = self.body()
            key = self.headers.get('Idempotency-Key')
            if (not key or len(key)>250 or set(body) != {'client_reference','order_reference','customer','address','items'}
                    or any(not isinstance(body[k],str) or not body[k] for k in ('client_reference','order_reference','customer','address'))
                    or not isinstance(body['items'],list) or not body['items']):
                raise ValueError('booking fields')
        except (ValueError,TypeError):
            return self.reply(400,{'error':'invalid booking'})
        conn = type(self).connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT body,booking_id,accepted_at FROM bookings WHERE key=?',(key,)).fetchone()
            if old:
                if json.loads(old[0]) != body:
                    conn.rollback()
                    return self.reply(409,{'error':'idempotency key already used'})
                bid,at,status = old[1],old[2],200
            else:
                bid,at,status = str(uuid.uuid4()),time.time(),201
                conn.execute('INSERT INTO bookings(key,body,booking_id,accepted_at) VALUES(?,?,?,?)',
                             (key,json.dumps(body,sort_keys=True),bid,at))
            conn.commit()
            self.reply(status,{**body,'booking_id':bid,'idempotency_key':key,'accepted_at':at})
        finally:
            conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('service',choices=['api','dispatch','carrier'])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if args.service == 'dispatch':
        dispatch()
    else:
        ThreadingHTTPServer(('127.0.0.1',8080 if args.service == 'api' else 8099),Api if args.service == 'api' else Carrier).serve_forever()
