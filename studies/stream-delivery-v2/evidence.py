"""Export and regrade the declared model attempt and two development controls."""
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0,str(REPO))
from pomdp_bench.benchmark import result_for
from pomdp_bench.collection import read_run, source_hashes
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.stream import DELIVERY_VERSION, suite

verify_requests = runpy.run_path(str(ROOT.parent/'stream-recovery-continuous-v1/verify.py'))['verify_requests']
render = runpy.run_path(str(ROOT.parent/'stream-recovery-v1/verify.py'))['render']
RUNS = {'positive':'stream-delivery-v2-positive-01',
        'negative':'stream-delivery-v2-negative-01',
        'model':'stream-delivery-v2-astra-max-01'}
FILES = ('plan.json','README.md','evidence.py','evidence.json.gz','trajectories.html.gz',
         'model-result.json','model-result.md',
         '../stream-recovery-continuous-v1/verify.py','../stream-recovery-v1/verify.py')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_hash(path):
    raw = path.read_bytes()
    return hashlib.sha256(raw if path.suffix=='.gz' else raw.replace(b'\r\n',b'\n')).hexdigest()


def load_evidence():
    return json.loads(gzip.decompress((ROOT/'evidence.json.gz').read_bytes()))


def check(data):
    plan = read(ROOT/'plan.json')
    if set(data)!=set(RUNS) or digest(suite(DELIVERY_VERSION))!=plan['suite_sha256']:
        raise ValueError('Attempt set or scenario changed')
    for label,item in data.items():
        manifest,records = item['manifest'],item['records']
        if (manifest['generator_version']!=DELIVERY_VERSION or manifest['suite_sha256']!=plan['suite_sha256']
                or manifest['expected_episodes']!=1 or len(records)!=1
                or manifest['framework_version']!=plan['framework_version']):
            raise ValueError('Incomplete or relabeled attempt')
        record = records[0]
        replay(record,manifest['cases'][0])
        if result_for(record)!=item['result']:
            raise ValueError('Result differs from retained evidence')
        for call in record['service_evidence']['calls']:
            audit = call['response'].get('audit')
            if audit and any(audit[k]!=plan['runtime'][k] for k in ('image','components')):
                raise ValueError('Runtime identity changed')
        if label=='model':
            if (manifest['working_tree_dirty'] or manifest['agents']!=plan['agents']
                    or record['agent']!=plan['agents'][0]
                    or manifest['wall_seconds_per_episode']!=plan['wall_seconds']
                    or manifest['conditions']!=plan['conditions'] or manifest['replicates']!=plan['replicates']):
                raise ValueError('Unfrozen or changed model attempt')
            verify_requests(record)
            settings = item['settings_check']
            if not settings['plan_bytes_unchanged'] or settings['plan_sha256']!=digest(plan):
                raise ValueError('Attempt configuration changed')
        elif record['agent']['kind']!='actions' or not manifest['working_tree_dirty']:
            raise ValueError('Development controls were relabeled as model evidence')
    positive,negative = (data[label]['records'][0]['grade'] for label in ('positive','negative'))
    if (not positive['success'] or positive['customers']['fulfilled_intents']!=12
            or negative['success'] or not negative['phases'][-1]['duplicate_bookings']):
        raise ValueError('Declared control behavior differs')
    if read(ROOT/'model-result.json')!=data['model']['result']:
        raise ValueError('Model result copy differs')


def readable(data):
    return render({'git_revision':data['model']['manifest']['git_revision'],
                   'records':[data[label]['records'][0] for label in RUNS]})


def export():
    if (ROOT/'evidence.json.gz').exists():
        raise ValueError('Published evidence already exists')
    data = {}
    for label,name in RUNS.items():
        run = REPO/'artifacts'/name
        manifest,records = read_run(run)
        data[label] = {'manifest':manifest,'records':records,'result':read(run/'result.json')}
        if label=='model':
            if manifest['source_sha256']!=source_hashes():
                raise ValueError('Collector source changed since the model run')
            data[label]['settings_check'] = read(run/'private/settings-check.json')
    model_run = REPO/'artifacts'/RUNS['model']
    for name in ('result.json','result.md'):
        (ROOT/('model-'+name)).write_bytes((model_run/name).read_bytes())
    check(data)
    (ROOT/'evidence.json.gz').write_bytes(gzip.compress((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
    (ROOT/'trajectories.html.gz').write_bytes(gzip.compress(readable(data).encode(),mtime=0))
    print('Exported one model attempt and two separately labeled development controls.')


def seal():
    if (ROOT/'execution.json').exists():
        raise ValueError('Published seal already exists')
    data = load_evidence()
    check(data)
    (ROOT/'execution.json').write_text(json.dumps({
        'source_commit':data['model']['manifest']['git_revision'],
        'file_sha256':{name:file_hash(ROOT/name) for name in FILES}},indent=2)+'\n',encoding='utf-8')


def verify():
    execution = read(ROOT/'execution.json')
    if set(execution['file_sha256'])!=set(FILES):
        raise ValueError('Incomplete evidence seal')
    for name,value in execution['file_sha256'].items():
        if file_hash(ROOT/name)!=value:
            raise ValueError('Published bytes changed: '+name)
    data = load_evidence()
    check(data)
    if (execution['source_commit']!=data['model']['manifest']['git_revision']
            or gzip.decompress((ROOT/'trajectories.html.gz').read_bytes()).decode()!=readable(data)):
        raise ValueError('Source binding or readable trajectory changed')
    print('Verified retained model attempt, public request projections, controls and independent business grading.')


if __name__=='__main__':
    {'export':export,'seal':seal,'verify':verify}[sys.argv[1]]()
