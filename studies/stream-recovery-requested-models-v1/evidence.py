"""Export and recheck all declared attempts without new model calls."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO))
from pomdp_bench.collection import read_run,source_hashes
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.model_io import request_body

SLUGS=('gpt6-sol','gpt6-luna','glm53','glm53-text')
render=runpy.run_path(str(ROOT.parent/'stream-recovery-v1/verify.py'))['render']
verify_session=runpy.run_path(str(ROOT.parent/'stream-recovery-continuous-v1/verify.py'))['verify_requests']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def hashed(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def check(slug,data):
    plan=read(ROOT/(slug+'-plan.json'))
    assert not data['working_tree_dirty']
    assert data['expected']==data['retained']==len(data['records'])==1
    assert len(data['cases'])==1
    assert digest({'generator_version':plan['generator_version'],'cases':data['cases']})==plan['suite_sha256']
    assert all(data['source_sha256'][k]==v for k,v in plan['environment_source_sha256'].items())
    assert data['settings_check']['settings_and_auth_bytes_unchanged']
    assert all(f['bytes_unchanged'] for f in data['settings_check']['files'])
    record=data['records'][0]
    assert record['agent']==plan['agents'][0]
    assert record['framework_version']==plan['framework_version']
    assert record['condition']=='open' and record['replicate']==0
    replay(record,data['cases'][0])
    if record['agent']['kind']=='responses_session':
        verify_session(record)
    else:
        for index,audit in enumerate(record['request_audit']):
            history=record['events'][:index]
            request={'protocol_version':1,'task':record['contract'],
                     'observation':history[-1]['observation'] if history else record['initial_observation'],
                     'history':history}
            raw=json.dumps(request_body(record['agent'],request),ensure_ascii=False,allow_nan=False).encode()
            assert hashlib.sha256(raw).hexdigest()==audit['request_sha256']
            native=record['agent']['kind']=='responses_tools'
            assert audit['declared_tools']==(['exec','finish'] if native else [])
            assert audit['tool_choice']==('required' if native else 'none')
            assert audit['max_response_bytes']==record['agent']['max_response_bytes']
    for call in record['service_evidence']['calls']:
        audit=call['response'].get('audit')
        if audit:
            assert audit['image']==plan['runtime']['image']
            assert audit['components']==plan['runtime']['components']


def export():
    for slug in SLUGS:
        dest=ROOT/(slug+'-evidence.json')
        if dest.exists():
            continue
        run=REPO/'artifacts'/('stream-'+slug+'-v1')
        manifest,records=read_run(run)
        assert manifest['source_sha256']==source_hashes()
        data={k:manifest[k] for k in ('git_revision','working_tree_dirty','source_sha256','cases')}
        data.update(expected=manifest['expected_episodes'],retained=len(records),records=records,
                    settings_check=read(run/'private/settings-check.json'))
        check(slug,data)
        with dest.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')
        (ROOT/(slug+'-trajectories.html')).write_text(render(data),encoding='utf-8',newline='\n')
        print('Exported '+slug)


def seal():
    files=['README.md','evidence.py','../stream-recovery-v1/verify.py',
           '../stream-recovery-continuous-v1/verify.py']
    for slug in SLUGS:
        files.extend(slug+suffix for suffix in ('-plan.json','-evidence.json','-trajectories.html'))
    data={'source_commits':{s:read(ROOT/(s+'-evidence.json'))['git_revision'] for s in SLUGS},
          'expected_episodes':4,'retained_episodes':4,
          'scope':'Recorded business regrading, complete attempt retention, declared plans and public requests. Native GPT opaque bytes are only hash commitments. GLM has stateless history; no controlled cross-model ranking.',
          'file_sha256':{f:hashed(ROOT/f) for f in files}}
    with (ROOT/'execution.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(data,stream,indent=2);stream.write('\n')


def verify():
    execution=read(ROOT/'execution.json')
    assert execution['expected_episodes']==execution['retained_episodes']==len(SLUGS)==4
    required={'README.md','evidence.py','../stream-recovery-v1/verify.py',
              '../stream-recovery-continuous-v1/verify.py'}
    required.update(s+suffix for s in SLUGS for suffix in ('-plan.json','-evidence.json','-trajectories.html'))
    assert required<=execution['file_sha256'].keys()
    for f,h in execution['file_sha256'].items():
        assert hashed(ROOT/f)==h,f
    sources=[]
    for slug in SLUGS:
        data=read(ROOT/(slug+'-evidence.json'))
        assert data['git_revision']==execution['source_commits'][slug]
        check(slug,data)
        assert (ROOT/(slug+'-trajectories.html')).read_text(encoding='utf-8')==render(data)
        sources.append(data['source_sha256'])
    assert all(source==sources[0] for source in sources)
    print('Verified all four retained attempts for three requested models, declared protocol differences, business regrading and public request projections.')


if __name__=='__main__':
    {'export':export,'seal':seal,'verify':verify}[sys.argv[1]]()
