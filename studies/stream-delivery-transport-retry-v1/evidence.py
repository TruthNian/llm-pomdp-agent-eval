"""Verify the independent follow-up, including every transport attempt."""
import gzip
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

helpers = runpy.run_path(str(ROOT.parent/'stream-delivery-v2/evidence.py'))
verify_requests,render,file_hash = (helpers[k] for k in ('verify_requests','render','file_hash'))
RUN = REPO/'artifacts/stream-delivery-transport-retry-astra-max-01'
FILES = ('plan.json','README.md','evidence.py','evidence.json.gz','trajectories.html.gz',
         'model-result.json','model-result.md','../stream-delivery-v2/evidence.py',
         '../stream-delivery-v2/execution.json','../stream-delivery-http-retry-v1/execution.json',
         '../stream-recovery-continuous-v1/verify.py',
         '../stream-recovery-v1/verify.py')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load():
    return json.loads(gzip.decompress((ROOT/'evidence.json.gz').read_bytes()))


def check(data):
    plan = read(ROOT/'plan.json')
    manifest,records = data['manifest'],data['records']
    if (manifest['working_tree_dirty'] or manifest['expected_episodes']!=1 or len(records)!=1
            or manifest['framework_version']!=plan['framework_version']
            or manifest['suite_sha256']!=plan['suite_sha256'] or manifest['agents']!=plan['agents']
            or manifest['wall_seconds_per_episode']!=plan['wall_seconds']
            or manifest['conditions']!=plan['conditions'] or manifest['replicates']!=plan['replicates']):
        raise ValueError('Unfrozen or changed follow-up attempt')
    original = json.loads(gzip.decompress((ROOT.parent/'stream-delivery-v2/evidence.json.gz').read_bytes()))
    for name,value in plan['environment_source_sha256'].items():
        if (manifest['source_sha256'].get(name)!=value
                or original['model']['manifest']['source_sha256'].get(name)!=value):
            raise ValueError('Incident or business acceptance changed')
    record = records[0]
    if record['agent']!=plan['agents'][0]:
        raise ValueError('Declared agent changed')
    replay(record,manifest['cases'][0])
    verify_requests(record)
    wires = 0
    for audit in record['request_audit']:
        attempts = audit.get('wire_attempts',[])
        if not 1<=len(attempts)<=3:
            raise ValueError('Unbounded or missing HTTP attempts')
        for index,attempt in enumerate(attempts):
            if (attempt['request_sha256']!=audit['request_sha256']
                    or not 0<attempt['timeout_seconds']<=plan['agents'][0]['timeout_seconds']):
                raise ValueError('Retried input or deadline changed')
            retryable = (attempt.get('http_status') in (500,502,503,504) or
                         attempt.get('retryable_transport') is True and
                         attempt['outcome'] in ('incomplete_response','transport_error','timeout'))
            if index<len(attempts)-1 and (not retryable
                    or not 1<=attempt['retry_delay_seconds']<=60):
                raise ValueError('Undeclared retry')
        wires += len(attempts)
    if record['usage']['requests']!=wires:
        raise ValueError('Network attempt count differs')
    for call in record['service_evidence']['calls']:
        audit = call['response'].get('audit')
        if audit and any(audit[k]!=plan['runtime'][k] for k in ('image','components')):
            raise ValueError('Runtime changed')
    if (not data['settings_check']['plan_bytes_unchanged']
            or data['settings_check']['plan_sha256']!=digest(plan)
            or result_for(record)!=data['result'] or read(ROOT/'model-result.json')!=data['result']):
        raise ValueError('Plan or result differs from retained evidence')


def readable(data):
    return render({'git_revision':data['manifest']['git_revision'],'records':data['records']})


def export():
    if (ROOT/'evidence.json.gz').exists():
        raise ValueError('Evidence already published')
    manifest,records = read_run(RUN)
    if manifest['source_sha256']!=source_hashes():
        raise ValueError('Collector source changed during the run')
    data = {'manifest':manifest,'records':records,'result':read(RUN/'result.json'),
            'settings_check':read(RUN/'private/settings-check.json')}
    for name in ('result.json','result.md'):
        (ROOT/('model-'+name)).write_bytes((RUN/name).read_bytes())
    check(data)
    (ROOT/'evidence.json.gz').write_bytes(gzip.compress((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
    (ROOT/'trajectories.html.gz').write_bytes(gzip.compress(readable(data).encode(),mtime=0))
    print('Exported the independent follow-up and all HTTP attempts.')


def seal():
    if (ROOT/'execution.json').exists():
        raise ValueError('Seal already published')
    data = load()
    check(data)
    (ROOT/'execution.json').write_text(json.dumps({
        'source_commit':data['manifest']['git_revision'],
        'file_sha256':{name:file_hash(ROOT/name) for name in FILES}},indent=2)+'\n',encoding='utf-8')


def verify():
    execution = read(ROOT/'execution.json')
    if set(execution['file_sha256'])!=set(FILES):
        raise ValueError('Incomplete follow-up seal')
    for name,value in execution['file_sha256'].items():
        if file_hash(ROOT/name)!=value:raise ValueError('Published file changed: '+name)
    data = load()
    check(data)
    if (execution['source_commit']!=data['manifest']['git_revision']
            or gzip.decompress((ROOT/'trajectories.html.gz').read_bytes()).decode()!=readable(data)):
        raise ValueError('Source binding or trajectory changed')
    print('Verified separate follow-up, identical-input HTTP retries, usage counts and independent business grading.')


if __name__=='__main__':
    {'export':export,'seal':seal,'verify':verify}[sys.argv[1]]()
