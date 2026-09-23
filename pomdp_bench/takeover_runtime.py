"""Real PostgreSQL incident, isolated shell, and external customer observations."""
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

HTTP_CLIENT = r'''
import json,sys,urllib.request,urllib.error
results=[]
for item in json.load(sys.stdin):
    body=json.dumps(item['body']).encode() if 'body' in item else None
    req=urllib.request.Request('http://127.0.0.1:8080'+item['path'], data=body,
        method=item.get('method','GET'), headers={'Content-Type':'application/json'})
    try:
        try: response=urllib.request.urlopen(req,timeout=3)
        except urllib.error.HTTPError as exc: response=exc
        with response:
            raw=response.read(1048577)
            try: value=json.loads(raw)
            except (ValueError,UnicodeError): value=None
            results.append({'status':response.status,'body':value})
    except (OSError,ValueError) as exc:
        results.append({'status':None,'error':type(exc).__name__})
print(json.dumps(results))
'''


def docker_config():
    data = json.loads(Path(os.environ['POMDP_TAKEOVER_CONFIG']).read_text(encoding='utf-8'))
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', data['image']):
        raise ValueError('Takeover requires an immutable local image ID')
    command = data.get('docker_command', ['docker'])
    if not isinstance(command, list) or not command or any(not isinstance(x, str) for x in command):
        raise ValueError('Invalid Docker command')
    if data.get('assets_sha256') != asset_hashes():
        raise ValueError('Rebuild the takeover image: source assets differ')
    return data


def asset_hashes():
    return {p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for p in sorted(Path(__file__).with_name('takeover_data').iterdir()) if p.is_file()}


def docker(command, args, *, data=None, timeout=120, limit=1048576):
    """Bound output and use argv/stdin, never execute candidate text on the host."""
    proc = subprocess.Popen(command + args, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    chunks, size, overflow = [], [0], threading.Event()

    def read():
        while block := proc.stdout.read(8192):
            remaining = limit - size[0]
            chunks.append(block[:remaining])
            size[0] += len(block[:remaining])
            if len(block) > remaining:
                overflow.set()
                proc.kill()
                break

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    def write():
        try:
            proc.stdin.write(data)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    writer = threading.Thread(target=write, daemon=True) if data is not None else None
    if writer:
        writer.start()
    expired = False
    try:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            proc.kill()
            proc.wait(timeout=10)
        reader.join(timeout=10)
        if writer:
            writer.join(timeout=10)
        if reader.is_alive():
            raise RuntimeError('Docker output pipe did not close')
        return {'exit_code': proc.returncode, 'output': b''.join(chunks).decode('utf-8', errors='replace'),
                'timed_out': expired, 'output_truncated': overflow.is_set()}
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.stdout.close()


def order(number, seed):
    rng = random.Random(f'{seed}/order/{number}')
    return {'reference': f'ORD-{rng.getrandbits(64):016x}', 'customer': f'C-{rng.randrange(10000,99999)}',
            'address': f'{rng.randrange(1,9000)} Cedar Street, Unit {rng.randrange(1,999)}',
            'items': [{'sku': f'SKU-{rng.randrange(100,999)}', 'quantity': rng.randrange(1,6),
                       'unit_cents': rng.randrange(100,25000)} for _ in range(rng.randrange(1,5))]}


def correct(expected, response):
    body = response.get('body')
    return (response.get('status') == 200 and isinstance(body, dict)
            and {k: body.get(k) for k in expected} == expected)


def assess(audit):
    """Recompute outcomes from customer receipts, never a supplied PASS boolean."""
    if audit is None:
        return {'delivered': False, 'accepted_orders': None, 'missing_or_changed': None,
                'post_restart_errors': None, 'new_write_errors': None, 'retry_errors': None,
                'observer_errors': 0,'traffic_read_failures':None,'traffic_write_failures':None}
    if (len(audit['initial_orders']) != 90 or len(audit['new_writes']) != 6
            or [x['expected_status'] for x in audit['retries']] != [200,409]):
        raise ValueError('Incomplete takeover audit')
    observer_errors = sum('observer_error' in batch for batch in audit['traffic'])
    expected = {x['reference']: x for x in audit['initial_orders']}
    if len(expected) != 90 or len(audit['initial_receipts']) != 90:
        raise ValueError('Incomplete initial customer receipts')
    for body, receipt in zip(audit['initial_orders'],audit['initial_receipts']):
        if receipt.get('status') != 201 or not correct(body,{**receipt,'status':200}):
            raise ValueError('Initial order was not accepted as specified')
    for batch in audit['traffic']:
        if batch['responses'][0].get('status') in (200, 201):
            expected[batch['order']['reference']] = batch['order']
    write_errors = 0
    for item in audit['new_writes']:
        response, body = item['response'], item['order']
        if response.get('status') not in (200, 201) or not isinstance(response.get('body'), dict) or any(response['body'].get(k) != v for k, v in body.items()):
            write_errors += 1
        if response.get('status') in (200, 201):
            expected[body['reference']] = body
    errors = []
    for key in ('reads', 'after_restart'):
        if [x['reference'] for x in audit[key]] != list(expected):
            raise ValueError('Incomplete or duplicate terminal observations')
        observed = {x['reference']: x['response'] for x in audit[key]}
        errors.append(sum(not correct(body, observed.get(ref, {})) for ref, body in expected.items()))
    retry_errors = sum(x['response'].get('status') != x['expected_status'] for x in audit['retries'])
    if audit['retries'][0]['response'].get('status') == 200 and not correct(audit['initial_orders'][0], audit['retries'][0]['response']):
        retry_errors += 1
    return {'delivered': not any((*errors, write_errors, retry_errors, observer_errors)), 'accepted_orders': len(expected),
            'missing_or_changed': errors[0], 'post_restart_errors': errors[1],
            'new_write_errors': write_errors, 'retry_errors': retry_errors,'observer_errors':observer_errors,
            'traffic_read_failures':sum(x['responses'][1].get('status') != 200 for x in audit['traffic'] if 'observer_error' not in x),
            'traffic_write_failures':sum(x['responses'][0].get('status') not in (200,201) for x in audit['traffic'] if 'observer_error' not in x)}


class Runtime:
    def __init__(self, case):
        self.case, self.config = case, docker_config()
        self.command, self.image = self.config.get('docker_command', ['docker']), self.config['image']
        self.name = 'pomdp-takeover-' + uuid.uuid4().hex[:12]
        self.client = self.name + '-customer'
        self.stop_event = threading.Event()
        self.traffic, self.initial, self.receipts = [], [], []
        self.started = time.monotonic()
        self.thread, self.audit = None, None
        self.keepalive = None
        try:
            # WSL system services alone do not keep a distribution running. A
            # caller-owned stdin process lasts exactly as long as this runtime.
            if self.config.get('keepalive_command'):
                self.keepalive = subprocess.Popen(self.config['keepalive_command'], stdin=subprocess.PIPE,
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.checked(['run', '-d', '--name', self.name, '--pull=never', '--network=none',
                          '--memory=1g', '--cpus=2', '--pids-limit=256', '--cap-drop=ALL',
                          '--cap-add=SETUID', '--cap-add=SETGID', '--cap-add=CHOWN', '--cap-add=FOWNER',
                          '--cap-add=DAC_OVERRIDE', '--cap-add=KILL', '--security-opt=no-new-privileges', self.image])
            self.start_client()
            for _ in range(60):
                result = self.shell("psql -h 127.0.0.1 -p 5432 -U postgres -Atc \"SELECT count(*) FROM pg_stat_replication WHERE state='streaming'\"")
                if result['exit_code'] == 0 and result['output'].strip() == '1':
                    break
                time.sleep(1)
            else:
                raise RuntimeError('Initial physical replication unavailable')
            for _ in range(30):
                if self.http([{'path':'/health'}])[0].get('status') == 200:
                    break
                time.sleep(.2)
            else:
                raise RuntimeError('Initial order API unavailable')
            self.accept(range(20))
            for _ in range(30):
                result = self.shell('psql -h 127.0.0.1 -p 5433 -U postgres -d orders -Atc "SELECT count(*) FROM orders"')
                if result['exit_code'] == 0 and result['output'].strip() == '20':
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Initial writes did not replicate')
            self.must_shell('mkdir -p /var/backups; pg_dump -h 127.0.0.1 -p 5432 -U postgres orders > /var/backups/orders.sql\n'
                            'gosu postgres pg_ctl -D /var/lib/postgresql/beta -w promote')
            self.accept(range(20,65))
            self.must_shell('printf \'{"read_port":5432,"write_port":5433}\\n\' > /srv/orders/config.json')
            self.accept(range(65,90))
            alpha_ids = {x['body']['order_id'] for x in self.receipts[20:65]}
            beta_ids = {x['body']['order_id'] for x in self.receipts[65:90]}
            if not alpha_ids & beta_ids:
                raise RuntimeError('Expected independently allocated surrogate IDs did not overlap')
            self.provenance = self.must_shell("psql -h 127.0.0.1 -p 5432 -U postgres -Atc 'SELECT timeline_id FROM pg_control_checkpoint();'\n"
                                             "psql -h 127.0.0.1 -p 5433 -U postgres -Atc 'CHECKPOINT; SELECT timeline_id FROM pg_control_checkpoint();'")
            self.thread = threading.Thread(target=self.workload, daemon=True)
            self.thread.start()
        except Exception:
            self.close()
            raise

    def checked(self, args, **kwargs):
        result = docker(self.command, args, **kwargs)
        if result['exit_code'] or result['timed_out'] or result['output_truncated']:
            raise RuntimeError('Docker operation failed: ' + result['output'][-1000:])
        return result['output']

    def start_client(self):
        self.checked(['run', '-d', '--name', self.client, '--pull=never', '--network=container:' + self.name,
                      '--read-only', '--cap-drop=ALL', '--pids-limit=32', '--memory=128m',
                      '--security-opt=no-new-privileges', '--entrypoint=/bin/sleep', self.image, 'infinity'])

    def shell(self, script):
        return docker(self.command, ['exec', '-i', '-w', '/srv/orders', self.name,
                                     'timeout', '--kill-after=2', '90', 'bash', '-s'], data=script.encode(), timeout=100)

    def must_shell(self, script):
        result = self.shell('set -e\n' + script)
        if result['exit_code']:
            raise RuntimeError('Initialization failed: ' + result['output'][-1000:])
        return result['output']

    def http(self, requests):
        raw = self.checked(['exec', '-i', self.client, 'python3', '-c', HTTP_CLIENT],
                           data=json.dumps(requests).encode(), timeout=max(30, len(requests)*4))
        result = json.loads(raw)
        if not isinstance(result, list) or len(result) != len(requests):
            raise ValueError('Invalid external client response')
        return result

    def accept(self, indices):
        bodies = [order(i, self.case['seed']) for i in indices]
        results = self.http([{'method':'POST','path':'/orders','body':x} for x in bodies])
        for body, response in zip(bodies, results):
            if response.get('status') != 201:
                raise RuntimeError('Initial business acceptance failed: '+str(response.get('status')))
            self.initial.append(body)
            self.receipts.append(response)

    def workload(self):
        number = 100
        while not self.stop_event.is_set():
            body = order(number, self.case['seed'])
            requests = [{'method':'POST','path':'/orders','body':body},
                        {'path':'/orders/' + self.initial[number % len(self.initial)]['reference']},
                        {'path':'/health'}]
            try:
                responses = self.http(requests)
                self.traffic.append({'elapsed':round(time.monotonic()-self.started,6), 'order':body,
                                     'responses':responses})
            except Exception as exc:
                self.traffic.append({'elapsed':round(time.monotonic()-self.started,6), 'order':body,
                                     'observer_error':type(exc).__name__, 'responses':[{'status':None}]})
            number += 1
            self.stop_event.wait(10)

    def observe_orders(self, expected):
        # The ordinary service contract allows 30 seconds for read visibility.
        # Keep every actual observation; retries here are external customer probes,
        # after handover, never guidance or automatic repair for the agent.
        deadline = time.monotonic() + 30
        observations, trials = {}, []
        pending = list(expected)
        while pending:
            responses = self.http([{'path':'/orders/'+x['reference']} for x in pending])
            for body,response in zip(pending,responses):
                observations[body['reference']] = response
                trials.append({'reference':body['reference'],'response':response,
                               'elapsed':round(time.monotonic()-self.started,6)})
            pending = [x for x in pending if not correct(x,observations[x['reference']])]
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(min(2,max(0,deadline-time.monotonic())))
        return ([{'reference':x['reference'],'response':observations[x['reference']]} for x in expected],trials)

    def final_audit(self):
        if self.audit is not None:
            return self.audit
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
            if self.thread.is_alive():
                raise RuntimeError('Customer workload did not stop')
        writes = []
        for body, response in zip([order(i,self.case['seed']) for i in range(10000,10006)],
                                  self.http([{'method':'POST','path':'/orders','body':order(i,self.case['seed'])}
                                             for i in range(10000,10006)])):
            writes.append({'order':body,'response':response})
        expected = self.initial + [x['order'] for x in self.traffic if x['responses'][0].get('status') in (200,201)]
        expected += [x['order'] for x in writes if x['response'].get('status') in (200,201)]
        reads, read_trials = self.observe_orders(expected)
        original = expected[0]
        conflict = {**original, 'address':original['address']+' Annex'}
        retries = [{'expected_status':status,'response':r} for status,r in zip((200,409),self.http([
            {'method':'POST','path':'/orders','body':original}, {'method':'POST','path':'/orders','body':conflict}]))]
        # Restart tests ordinary durability; it does not restore a snapshot or repair anything.
        restart = docker(self.command,['restart','--time','10',self.name],timeout=45)
        docker(self.command,['rm','-f','-v',self.client],timeout=30)
        state = json.loads(self.checked(['inspect','--format','{{json .State}}',self.name]))
        if state['Running']:
            self.start_client()
            for _ in range(30):
                if self.http([{'path':'/health'}])[0].get('status') == 200:
                    break
                time.sleep(1)
            after, after_trials = self.observe_orders(expected)
        else:
            # No HTTP request is claimed here: the inspected target could not run.
            after = [{'reference':x['reference'],'response':{'status':None,'unavailable':'target_not_running'}} for x in expected]
            after_trials = []
        self.audit = {'initial_orders':copy.deepcopy(self.initial),'initial_receipts':copy.deepcopy(self.receipts),
                      'traffic':copy.deepcopy(self.traffic),
                      'new_writes':writes,'reads':reads,'after_restart':after,'retries':retries,
                      'read_trials':read_trials,'after_restart_trials':after_trials,
                      'image':self.image,'initial_timelines':self.provenance,'restart':restart,'restart_state':state}
        return self.audit

    def call(self, action):
        valid = isinstance(action,dict) and not set(action)-{'command','target'}
        command = action.get('command') if valid else None
        if command == 'exec' and isinstance(action.get('target'),str) and len(action['target']) <= 131072:
            result = self.shell(action['target'])
            audit = None
        elif command in ('finish','__abort__'):
            result = {'handover':True} if command == 'finish' else {'terminated':True}
            try:
                audit = self.final_audit()
            except Exception as exc:
                # Preserve a terminal attempt without recasting observer failure
                # as evidence of cognitive difficulty or inventing business reads.
                return {'result':result,'audit':None,'audit_error':type(exc).__name__,'state_sha256':None}
        else:
            result, audit = {'error':'Unknown command or invalid arguments'}, None
        return {'result':result,'audit':audit,'state_sha256':None}

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
        for name in (self.client,self.name):
            docker(self.command,['rm','-f','-v',name],timeout=30)
        if self.keepalive is not None:
            self.keepalive.stdin.close()
            try:
                self.keepalive.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.keepalive.kill()
