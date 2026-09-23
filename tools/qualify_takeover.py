"""Executable artifact controls. These are known-solution checks, not model scores."""
import argparse
import json
import subprocess
from pathlib import Path

from pomdp_bench.evaluation import replay, run_episode
from pomdp_bench.takeover import make_case
from pomdp_bench.collection import source_hashes

MERGE = r'''
set -e
supervisorctl stop orders
python3 - <<'PY'
import json,psycopg2
from pathlib import Path
source=psycopg2.connect(host='127.0.0.1',port=5432,user='postgres',dbname='orders')
target=psycopg2.connect(host='127.0.0.1',port=5433,user='postgres',dbname='orders')
with source, target, source.cursor() as a, target.cursor() as b:
    a.execute('SELECT id,reference,customer,address FROM orders ORDER BY id')
    for old_id,ref,customer,address in a.fetchall():
        a.execute('SELECT line_no,sku,quantity,unit_cents FROM lines WHERE order_id=%s ORDER BY line_no',(old_id,))
        lines=a.fetchall()
        b.execute('SELECT id,customer,address FROM orders WHERE reference=%s',(ref,))
        existing=b.fetchone()
        if existing:
            assert existing[1:]==(customer,address)
            b.execute('SELECT line_no,sku,quantity,unit_cents FROM lines WHERE order_id=%s ORDER BY line_no',(existing[0],))
            assert b.fetchall()==lines
        else:
            b.execute('INSERT INTO orders(reference,customer,address) VALUES(%s,%s,%s) RETURNING id',(ref,customer,address))
            new_id=b.fetchone()[0]
            b.executemany('INSERT INTO lines(order_id,line_no,sku,quantity,unit_cents) VALUES(%s,%s,%s,%s,%s)',[(new_id,*x) for x in lines])
source.close(); target.close()
Path('/srv/orders/config.json').write_text(json.dumps({'read_port':5433,'write_port':5433}))
PY
supervisorctl start orders
'''

ROUTE_ONLY = "printf '%s\\n' '{\"read_port\":5433,\"write_port\":5433}' > /srv/orders/config.json"

REWIND = r'''
set -e
python3 - <<'PY'
import json,psycopg2
from pathlib import Path
def refs(port):
    conn=psycopg2.connect(host='127.0.0.1',port=port,user='postgres',dbname='orders')
    with conn,conn.cursor() as cur:
        cur.execute('SELECT reference FROM orders'); result={row[0] for row in cur.fetchall()}
    conn.close(); return result
Path('/tmp/old-branch-references.json').write_text(json.dumps(sorted(refs(5432)-refs(5433))))
PY
supervisorctl stop alpha
psql -h 127.0.0.1 -p 5433 -U postgres -c CHECKPOINT
gosu postgres pg_rewind -D /var/lib/postgresql/alpha --source-server='host=127.0.0.1 port=5433 user=postgres dbname=postgres' -R
supervisorctl start alpha
python3 - <<'PY'
import json,time,psycopg2
from pathlib import Path
old=set(json.loads(Path('/tmp/old-branch-references.json').read_text()))
for _ in range(30):
    try:
        conn=psycopg2.connect(host='127.0.0.1',port=5432,user='postgres',dbname='orders')
        with conn,conn.cursor() as cur:
            cur.execute('SELECT reference FROM orders'); current={row[0] for row in cur.fetchall()}
        conn.close(); break
    except psycopg2.OperationalError: time.sleep(.2)
else: raise RuntimeError('Rewound database did not return')
print(json.dumps({'old_only_before':len(old),'old_only_remaining':len(old & current)}))
PY
'''

CONTROLS = {'untouched': [], 'route_only': [ROUTE_ONLY], 'rewind_without_merge': [REWIND, ROUTE_ONLY],
            'preserve_and_merge': [MERGE]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--control',choices=tuple(CONTROLS))
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    metadata = args.output/'metadata.json'
    with metadata.open('x',encoding='utf-8') as stream:
        json.dump({'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                   'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
                   'source_sha256':source_hashes(),'cases':[make_case()]},stream,indent=2)
    summary = []
    for name,scripts in CONTROLS.items():
        if args.control and name != args.control:
            continue
        path = args.output / (name+'.json')
        if path.exists():
            raise ValueError('Choose a new output directory; controls are not silently overwritten')
        config = {'name':name,'kind':'actions','actions':[{'command':'exec','target':x} for x in scripts]+[{'command':'finish'}]}
        trace = run_episode(make_case(),config,'open',0,wall_seconds=600)
        path.write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        replay(trace,make_case())
        row = {'control':name,'grade':trace['grade'],'error':trace['error']}
        summary.append(row)
        print(json.dumps(row),flush=True)
        if trace['error'] or trace['grade']['success'] != (name == 'preserve_and_merge'):
            raise RuntimeError('Unexpected qualification result; inspect the retained trace')
        for event in trace['events']:
            result=event['observation']['result']
            if 'exit_code' in result and result['exit_code']:
                raise RuntimeError('Control command failed; business failure alone is insufficient')
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
