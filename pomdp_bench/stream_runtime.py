"""PostgreSQL, Debezium, Kafka and an independently persisted dispatch ledger.

Prototype execution only until qualification and a versioned ceiling screen are
frozen. The source of truth for accepted work is the external customer's receipts.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import threading
import time
import uuid

from .takeover_runtime import docker, HTTP_CLIENT

CLIENT = HTTP_CLIENT.replace("'http://127.0.0.1:8080'+item['path']", "'http://127.0.0.1:'+str(item.get('port',8080))+item['path']")
ROOT = Path(__file__).with_name('stream_data')


def asset_hashes():
    return {p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file()}


def configuration():
    config = json.loads(Path(os.environ['POMDP_STREAM_CONFIG']).read_text(encoding='utf-8'))
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',config['image']):
        raise ValueError('Immutable stream image required')
    if config.get('assets_sha256') != asset_hashes():
        raise ValueError('Rebuild the stream image: deployed assets changed')
    argv = config.get('docker_command',['docker'])
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv):
        raise ValueError('Invalid Docker command')
    return config


def commands(number, seed=2718, *, ending='release', amend=False):
    rng = random.Random(f'{seed}/commerce/{number}')
    ref = 'ORD-'+uuid.uuid5(uuid.NAMESPACE_URL,f'{seed}/order/{number}').hex[:18]
    payload = {'customer':f'C-{rng.randrange(10000,99999)}',
               'address':f'{rng.randrange(1,9000)} Rowan Road, Unit {rng.randrange(1,999)}',
               'items':[{'sku':f'SKU-{rng.randrange(100,999)}','quantity':rng.randrange(1,5),
                         'unit_cents':rng.randrange(100,9000)} for _ in range(rng.randrange(1,4))]}
    result = []
    def add(kind, revision, data=None):
        result.append({'request_id':str(uuid.uuid5(uuid.NAMESPACE_URL,f'{seed}/command/{number}/{kind}/{revision}')),
                       'reference':ref,'revision':revision,'kind':kind,**(data or {})})
    add('draft',1,payload)
    revision = 2
    if amend:
        payload = {**payload,'address':payload['address']+' Annex'}
        add('amend',revision,payload)
        revision += 1
    if ending:
        add(ending,revision)
    return result


def initial_batches(seed=2718):
    common = [x for n in range(12) for x in commands(n,seed,ending='release' if n<8 else None)]
    branches = []
    for start,common_index in ((100,8),(200,10)):
        branch = commands(common_index,seed,amend=True)[1:]
        branch += commands(common_index+1,seed,ending='cancel')[1:]
        branch += [x for n in range(start,start+24)
                   for x in commands(n,seed,ending='cancel' if n%4==0 else 'release',amend=n%3==0)]
        branches.append(branch)
    return common,*branches


def matches(expected,observed):
    if not isinstance(observed,dict):
        return False
    try:
        return (json.dumps(expected,sort_keys=True,allow_nan=False)==
                json.dumps({k:observed.get(k) for k in expected},sort_keys=True,allow_nan=False))
    except (ValueError,TypeError):
        return False


def obligations(records):
    """Derive accepted business work from client requests and their receipts."""
    orders, releases, requests = {}, {}, {}
    receipt_errors = 0
    fields = ('reference','revision','customer','address','items','status')
    for item in records:
        response,body = item['response'],item['body']
        if response.get('status') not in (200,201):
            continue
        key,reference,kind = body['request_id'],body['reference'],body['kind']
        if key in requests:
            original,snapshot = requests[key]
            if original != body:
                receipt_errors += 1
                continue
        else:
            current = orders.get(reference)
            if (kind=='draft' and current is not None or kind!='draft' and
                    (current is None or current['status']!='draft' or body['revision']<=current['revision'])):
                receipt_errors += 1
                continue
            if kind=='draft':
                snapshot = {k:copy.deepcopy(body[k]) for k in ('reference','revision','customer','address','items')}
                snapshot['status'] = 'draft'
            else:
                snapshot = copy.deepcopy(current)
                snapshot['revision'] = body['revision']
                if kind=='amend':
                    snapshot.update({k:copy.deepcopy(body[k]) for k in ('customer','address','items')})
                else:
                    snapshot['status'] = 'released' if kind=='release' else 'cancelled'
            orders[reference] = snapshot
            requests[key] = (copy.deepcopy(body),snapshot)
            if kind=='release':
                releases[key] = {'client_reference':key,'order_reference':reference,
                                 **{k:copy.deepcopy(snapshot[k]) for k in ('customer','address','items')}}
        value = response.get('body') if isinstance(response.get('body'),dict) else {}
        reported = value.get('order') if isinstance(value.get('order'),dict) else {}
        if value.get('event_id')!=key or not matches({k:snapshot[k] for k in fields},reported):
            receipt_errors += 1
    return orders,releases,receipt_errors


def booking_errors(expected,observed):
    groups = {}
    for value in observed:
        groups.setdefault(value.get('client_reference'),[]).append(value)
    missing = sum(not groups.get(key) for key in expected)
    duplicates = sum(max(0,len(values)-1) for key,values in groups.items() if key in expected)
    unexpected = sum(len(values) for key,values in groups.items() if key not in expected)
    changed = sum(not matches(expected[key],value)
                  for key,values in groups.items() if key in expected for value in values)
    return {'missing_bookings':missing,'duplicate_bookings':duplicates,
            'unexpected_bookings':unexpected,'changed_bookings':changed}


def assess(audit):
    if audit is None:
        return {'delivered':False,'observer_errors':0,'phases':[]}
    expected_initial = [x for batch in initial_batches(audit['seed']) for x in batch]
    if ([x['body'] for x in audit['initial']] != expected_initial or len(audit['phases'])!=2
            or any(x['response'].get('status')!=201 for x in audit['initial'])):
        raise ValueError('Incomplete stream incident audit')
    records = list(audit['initial']) + [x for batch in audit['traffic'] for x in batch['commands']]
    observer_errors = sum('observer_error' in batch for batch in audit['traffic'])
    summaries = []
    for number,phase in enumerate(audit['phases']):
        bodies = [x for n in range(9000+number*10,9006+number*10)
                  for x in commands(n,audit['seed'],ending='cancel' if n%3==0 else 'release',amend=n%2==0)]
        if [x['body'] for x in phase['commands']] != bodies:
            raise ValueError('Terminal customer workload changed')
        records += phase['commands']
        orders,releases,receipt_errors = obligations(records)
        if [x['reference'] for x in phase['reads']] != list(orders):
            raise ValueError('Incomplete terminal order observations')
        order_errors = sum(item['response'].get('status')!=200 or
                           not matches(orders[item['reference']],item['response'].get('body'))
                           for item in phase['reads'])
        summary = {'accepted_orders':len(orders),'accepted_releases':len(releases),
                   'order_errors':order_errors,'receipt_errors':receipt_errors,
                   'new_command_errors':sum(x['response'].get('status')!=201 for x in phase['commands']),
                   **booking_errors(releases,phase['bookings'])}
        summaries.append(summary)
    if len(audit['retry_probes'])!=2:
        raise ValueError('Missing request identity probes')
    retry_errors = sum(x['response'].get('status')!=status for x,status in zip(audit['retry_probes'],(200,409)))
    _,_,replay_errors = obligations(records+[audit['retry_probes'][0]])
    retry_errors += max(0,replay_errors-summaries[-1]['receipt_errors'])
    accepted = [x for batch in audit['traffic'] for x in batch['commands']]
    return {'delivered':not(observer_errors or retry_errors or any(v for phase in summaries for k,v in phase.items()
                                                                 if k not in ('accepted_orders','accepted_releases'))),
            'observer_errors':observer_errors,'retry_errors':retry_errors,'phases':summaries,
            'traffic_write_failures':sum(x['response'].get('status')not in(200,201) for x in accepted)}


class Runtime:
    def __init__(self, case=None, *, progress=None, traffic=True):
        self.case = case or {'seed':2718}
        self.config = configuration()
        self.command = self.config.get('docker_command',['docker'])
        self.image = self.config['image']
        self.name = 'pomdp-stream-'+uuid.uuid4().hex[:12]
        self.client,self.carrier,self.volume = self.name+'-customer',self.name+'-carrier',self.name+'-ledger'
        self.stop_event = threading.Event()
        self.thread,self.keepalive,self.audit = None,None,None
        self.initial,self.traffic = [],[]
        self.started = time.monotonic()
        self.provenance = {}
        progress = progress or (lambda _:None)
        try:
            if self.config.get('keepalive_command'):
                self.keepalive = subprocess.Popen(self.config['keepalive_command'],stdin=subprocess.PIPE,
                                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            progress('Starting real database and stream processes')
            self.checked(['run','-d','--name',self.name,'--pull=never','--network=none',
                          '--memory=4g','--cpus=3','--pids-limit=1024','--cap-drop=ALL',
                          '--cap-add=SETUID','--cap-add=SETGID','--cap-add=CHOWN','--cap-add=FOWNER',
                          '--cap-add=DAC_OVERRIDE','--cap-add=KILL','--security-opt=no-new-privileges',self.image])
            self.checked(['volume','create',self.volume])
            self.start_clients()
            self.wait_ready()
            connector = json.loads((ROOT/'connector.json').read_text())
            response = self.http([{'port':8083,'path':'/connectors','method':'POST','body':connector}])[0]
            if response.get('status') != 201:
                raise RuntimeError('Connector registration failed: '+str(response))
            self.wait_connector()
            progress('Executing accepted common history through the real pipeline')
            common,alpha,beta = initial_batches(self.case['seed'])
            self.accept(common)
            self.wait_bookings(8)
            count = len(common)
            for _ in range(60):
                value = self.shell(f"psql -h 127.0.0.1 -p 5433 -U postgres -d commerce -Atc 'SELECT count(*) FROM requests'")
                if value['exit_code']==0 and value['output'].strip()==str(count):
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Common history did not physically replicate')
            self.must_shell('install -d -o postgres -g postgres -m 700 /var/backups/commerce-base\n'
                            'gosu postgres pg_basebackup -h 127.0.0.1 -p 5432 -U postgres -D /var/backups/commerce-base -X stream --checkpoint=fast')
            progress('Executing the partition, promotion and acknowledged branch histories')
            self.must_shell("psql -h 127.0.0.1 -p 5433 -U postgres -v ON_ERROR_STOP=1 -c \"ALTER SYSTEM SET primary_conninfo='host=127.0.0.1 port=59999 user=postgres'\"\n"
                            "psql -h 127.0.0.1 -p 5433 -U postgres -v ON_ERROR_STOP=1 -c 'SELECT pg_reload_conf();'\n"
                            "gosu postgres pg_ctl -D /var/lib/postgresql/beta -w promote")
            self.accept(alpha[:31])
            self.wait_bookings(18)
            self.must_shell('supervisorctl stop connect')
            self.accept(alpha[31:])
            self.must_shell("python3 - <<'PY'\nimport json\nfrom pathlib import Path\np=Path('/etc/commerce/application.json')\nc=json.loads(p.read_text());c['port']=5433;p.write_text(json.dumps(c)+'\\n')\nPY")
            self.accept(beta)
            # Complete a real WAL archive before the destructive operation. Neither
            # this archive receipt nor the evaluator's provenance is agent feedback.
            self.provenance['before_rewind'] = self.must_shell("psql -h 127.0.0.1 -p 5432 -U postgres -d commerce -Atc 'SELECT count(*) FROM orders; SELECT pg_current_wal_lsn();'\n"
                                                               "psql -h 127.0.0.1 -p 5432 -U postgres -Atc 'SELECT pg_switch_wal();'")
            for _ in range(60):
                pending = self.shell("find /var/lib/postgresql/alpha/pg_wal/archive_status -name '*.ready' -print")
                if pending['exit_code']==0 and not pending['output'].strip():
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Old-branch WAL was not archived')
            progress('Executing actual destructive rewind; ordinary backup and WAL archive remain')
            self.provenance['rewind'] = self.must_shell("supervisorctl stop alpha\n"
                "gosu postgres pg_rewind --target-pgdata=/var/lib/postgresql/alpha --source-server='host=127.0.0.1 port=5433 user=postgres dbname=postgres'\n"
                "printf \"primary_conninfo = 'host=127.0.0.1 port=5433 user=postgres'\\n\" >> /var/lib/postgresql/alpha/postgresql.auto.conf\n"
                "touch /var/lib/postgresql/alpha/standby.signal\n"
                "chown postgres:postgres /var/lib/postgresql/alpha/standby.signal\n"
                "supervisorctl start alpha\n"
                "supervisorctl start connect")
            for _ in range(60):
                result = self.shell("psql -h 127.0.0.1 -p 5432 -U postgres -d commerce -Atc 'SELECT count(*) FROM orders'")
                if result['exit_code']==0 and result['output'].strip()=='36':
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Rewound standby did not recover the new timeline')
            self.provenance['databases'] = self.must_shell("for port in 5432 5433; do psql -h 127.0.0.1 -p $port -U postgres -d commerce -Atc 'SELECT timeline_id FROM pg_control_checkpoint(); SELECT count(*),min(id),max(id) FROM outbox;'; done")
            self.provenance['connector'] = self.http([{'port':8083,'path':'/connectors/commerce-outbox/status'}])[0]
            self.provenance['carrier_bookings'] = len(self.bookings())
            progress('Incident ready; only ordinary operational surfaces enter model observations')
            if traffic:
                self.thread = threading.Thread(target=self.workload,daemon=True)
                self.thread.start()
        except Exception:
            progress('STARTUP_DIAGNOSTICS '+json.dumps(self.shell('supervisorctl status; tail -20 /var/log/commerce/*.log')))
            self.close()
            raise

    def checked(self,args,**kwargs):
        result = docker(self.command,args,**kwargs)
        if result['exit_code'] or result['timed_out'] or result['output_truncated']:
            raise RuntimeError('Docker operation failed: '+result['output'][-2500:])
        return result['output']

    def start_clients(self):
        self.checked(['run','-d','--name',self.client,'--pull=never','--network=container:'+self.name,
                      '--read-only','--cap-drop=ALL','--memory=192m','--pids-limit=32',
                      '--security-opt=no-new-privileges','--entrypoint=/bin/sleep',self.image,'infinity'])
        self.checked(['run','-d','--name',self.carrier,'--pull=never','--network=container:'+self.name,
                      '--read-only','--cap-drop=ALL','--memory=192m','--pids-limit=64',
                      '--security-opt=no-new-privileges','--mount','type=volume,src='+self.volume+',dst=/data',
                      '--entrypoint=/usr/bin/python3',self.image,'-u','/srv/commerce/service.py','carrier'])

    def shell(self,script):
        return docker(self.command,['exec','-i','-w','/srv/commerce',self.name,
                                    'timeout','--kill-after=2','90','bash','-s'],data=script.encode(),timeout=100)

    def must_shell(self,script):
        value = self.shell('set -e\n'+script)
        if value['exit_code'] or value['timed_out'] or value['output_truncated']:
            raise RuntimeError('Initialization failed: '+value['output'][-2500:])
        return value['output']

    def http(self,requests):
        raw = self.checked(['exec','-i',self.client,'python3','-c',CLIENT],
                           data=json.dumps(requests).encode(),timeout=max(30,len(requests)*4),limit=4194304)
        result = json.loads(raw)
        if not isinstance(result,list) or len(result)!=len(requests):
            raise ValueError('Invalid external client observation')
        return result

    def wait_ready(self):
        for _ in range(120):
            statuses = self.http([{'path':'/health'},{'port':8099,'path':'/health'},{'port':8083,'path':'/'}])
            if all(item.get('status')==200 for item in statuses):
                return
            time.sleep(1)
        raise RuntimeError('Database/API/Connect startup failed: '+self.shell('supervisorctl status; tail -20 /var/log/commerce/connect.log')['output'])

    def wait_connector(self):
        for _ in range(90):
            response = self.http([{'port':8083,'path':'/connectors/commerce-outbox/status'}])[0]
            value = response.get('body') or {}
            if value.get('tasks') and all(t.get('state')=='RUNNING' for t in value['tasks']):
                return
            time.sleep(1)
        raise RuntimeError('CDC connector did not start: '+str(response))

    def bookings(self):
        result = self.http([{'port':8099,'path':'/bookings'}])[0]
        if result.get('status') != 200 or not isinstance(result.get('body',{}).get('bookings'),list):
            raise RuntimeError('Carrier API observation failed')
        return result['body']['bookings']

    def wait_bookings(self,count):
        for _ in range(90):
            values = self.bookings()
            if len(values)==count:
                return
            if len(values)>count:
                raise RuntimeError('Unexpected duplicate during qualification setup')
            time.sleep(1)
        raise RuntimeError('Initial pipeline did not deliver: '+self.shell('tail -30 /var/log/commerce/dispatch.log')['output'])

    def submit(self,bodies):
        responses = self.http([{'path':'/commands','method':'POST','body':body} for body in bodies])
        return [{'body':copy.deepcopy(body),'response':response} for body,response in zip(bodies,responses)]

    def accept(self,bodies):
        records = self.submit(bodies)
        if any(x['response'].get('status')!=201 for x in records):
            raise RuntimeError('Initial command not accepted: '+json.dumps(records))
        self.initial.extend(records)

    def workload(self):
        number = 1000
        while not self.stop_event.is_set():
            batch = {'elapsed':round(time.monotonic()-self.started,6),'commands':[]}
            try:
                batch['commands'] = self.submit(commands(number,self.case['seed']))
            except Exception as exc:
                batch['observer_error'] = type(exc).__name__
            self.traffic.append(batch)
            number += 1
            self.stop_event.wait(12)

    def persistent_bookings(self):
        # Read the independent ledger, not a response the operated host could forge.
        code = "import sqlite3,json; c=sqlite3.connect('file:/data/carrier.sqlite?mode=ro',uri=True); print(json.dumps([{**json.loads(b),'idempotency_key':k,'booking_id':i,'accepted_at':t} for k,b,i,t in c.execute('SELECT key,body,booking_id,accepted_at FROM bookings ORDER BY id')]))"
        return json.loads(self.checked(['exec',self.carrier,'python3','-c',code],limit=4194304))

    def observe(self,records):
        orders,releases,_ = obligations(records)
        deadline = time.monotonic()+60
        trials = []
        while True:
            responses = self.http([{'path':'/orders/'+ref} for ref in orders])
            reads = [{'reference':ref,'response':response} for ref,response in zip(orders,responses)]
            bookings = self.persistent_bookings()
            trials.append({'elapsed':round(time.monotonic()-self.started,6),'reads':reads,'bookings':bookings})
            correct = all(x['response'].get('status')==200 and
                          matches(orders[x['reference']],x['response'].get('body'))
                          for x in reads)
            if correct and not any(booking_errors(releases,bookings).values()) or time.monotonic()>=deadline:
                return {'reads':reads,'bookings':bookings,'trials':trials}
            time.sleep(min(2,max(0,deadline-time.monotonic())))

    def final_audit(self):
        if self.audit is not None:
            return self.audit
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
            if self.thread.is_alive():
                raise RuntimeError('Customer workload did not stop')
        records = list(self.initial)+[x for batch in self.traffic for x in batch['commands']]
        phases = []
        restart = None
        for number in range(2):
            if number:
                restart = docker(self.command,['restart','--time','20',self.name],timeout=75)
                # New network namespace; recreate observers and the provider process.
                # The carrier's existing volume is reused verbatim, never restored.
                for name in (self.client,self.carrier):
                    docker(self.command,['rm','-f',name],timeout=30)
                self.start_clients()
                for _ in range(60):
                    responses = self.http([{'path':'/health'},{'port':8099,'path':'/health'}])
                    if all(x.get('status')==200 for x in responses):
                        break
                    time.sleep(1)
            inputs = [x for n in range(9000+number*10,9006+number*10)
                      for x in commands(n,self.case['seed'],ending='cancel' if n%3==0 else 'release',amend=n%2==0)]
            new = self.submit(inputs)
            records += new
            phases.append({'commands':new,**self.observe(records)})
        original = self.initial[0]['body']
        conflict = {**original,'address':original['address']+' altered'}
        retries = self.submit([original,conflict])
        self.audit = {'seed':self.case['seed'],'initial':copy.deepcopy(self.initial),
                      'traffic':copy.deepcopy(self.traffic),'phases':phases,'retry_probes':retries,
                      'image':self.image,'components':self.config['components'],
                      'initial_provenance':self.provenance,'restart':restart}
        return self.audit

    def call(self,action):
        valid = isinstance(action,dict) and not set(action)-{'command','target'}
        command = action.get('command') if valid else None
        if command=='exec' and isinstance(action.get('target'),str) and len(action['target'])<=131072:
            result,audit = self.shell(action['target']),None
        elif command in ('finish','__abort__'):
            result = {'handover':True} if command=='finish' else {'terminated':True}
            try:
                audit = self.final_audit()
            except Exception as exc:
                return {'result':result,'audit':None,'audit_error':type(exc).__name__,'state_sha256':None}
        else:
            result,audit = {'error':'Unknown command or invalid arguments'},None
        return {'result':result,'audit':audit,'state_sha256':None}

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
        for name in (self.client,self.carrier,self.name):
            docker(self.command,['rm','-f','-v',name],timeout=40)
        docker(self.command,['volume','rm',self.volume],timeout=30)
        if self.keepalive is not None:
            self.keepalive.stdin.close()
            try:
                self.keepalive.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.keepalive.kill()
