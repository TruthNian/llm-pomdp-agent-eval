"""Regrade business outcomes and reconstruct continuous public input projections."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.native_session import NativeSession, fingerprint

ROOT=Path(__file__).resolve().parent
render=runpy.run_path(str(ROOT.parent/'stream-recovery-v1/verify.py'))['render']


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def verify_requests(record):
    initial={'protocol_version':1,'task':record['contract'],'observation':record['initial_observation'],'history':[]}
    payload=NativeSession().request(record['agent'],initial)
    identities=set()
    for index,audit in enumerate(record['request_audit']):
        if (fingerprint(payload)!=audit['input_projection_sha256']
                or audit['protocol']!='responses_session' or audit['declared_tools']!=['exec','finish']
                or audit['tool_choice']!='required' or audit['max_response_bytes']!=record['agent']['max_response_bytes']):
            raise ValueError('Continuous public input projection differs')
        if audit['outcome']!='action':
            if index!=len(record['request_audit'])-1 or index!=len(record['events']):
                raise ValueError('Failed request is not a retained terminal attempt')
            continue
        items=audit['response_items']
        calls=[item for item in items if item['type']=='function_call']
        if len(calls)!=1 or calls[0]['call_id'] in identities:
            raise ValueError('Ambiguous or reused call identity')
        call=calls[0];identities.add(call['call_id'])
        action={'command':call['name'],**json.loads(call['arguments'])}
        if action!=record['events'][index]['action']:
            raise ValueError('Call differs from executed action')
        for item in items:
            if item['type']=='reasoning':
                if (set(item)-{'type','id','encrypted_content_sha256','summary_sha256'}
                        or not all(re.fullmatch('[0-9a-f]{64}',item[key])
                                   for key in ('encrypted_content_sha256','summary_sha256'))):
                    raise ValueError('Unredacted or malformed opaque state')
        if sum(x['type']=='reasoning' for x in items)!=audit['preserved_reasoning_items']:
            raise ValueError('Reasoning-state count differs')
        payload['input'].extend(items)
        payload['input'].append({'type':'function_call_output','call_id':call['call_id'],
                                 'output':json.dumps(record['events'][index]['observation'],ensure_ascii=False,allow_nan=False)})


def main():
    plan,data,execution=read('plan.json'),read('model-evidence.json'),read('execution.json')
    required={'plan.json','README.md','model-evidence.json','trajectories.html','verify.py',
              'development-preflight-01.json','development-preflight-02.json','../stream-recovery-v1/verify.py'}
    if not required<=execution['file_sha256'].keys():raise ValueError('Incomplete evidence binding')
    for name,expected in execution['file_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('Published bytes changed: '+name)
    if (data['git_revision']!=execution['source_commit'] or data['working_tree_dirty']
            or data['expected']!=1 or data['retained']!=1 or len(data['records'])!=1 or len(data['cases'])!=1):
        raise ValueError('Unfrozen or incomplete continuous attempt')
    if digest({'generator_version':plan['generator_version'],'cases':data['cases']})!=plan['suite_sha256']:
        raise ValueError('Scenario changed')
    controls=read('../stream-recovery-v1/control-evidence.json')
    for key,value in plan['environment_source_sha256'].items():
        if data['source_sha256'].get(key)!=value or controls['source_sha256'].get(key)!=value:
            raise ValueError('Qualified environment changed')
    record=data['records'][0]
    if (record['agent']!=plan['agents'][0] or record['framework_version']!=plan['framework_version']
            or record['condition']!='open' or record['replicate']!=0):
        raise ValueError('Declared attempt changed')
    replay(record,data['cases'][0]);verify_requests(record)
    for call in record['service_evidence']['calls']:
        audit=call['response'].get('audit')
        if audit and (audit['image']!=plan['runtime']['image'] or audit['components']!=plan['runtime']['components']):
            raise ValueError('Runtime changed')
    settings=data['settings_check']
    if not settings['settings_and_auth_bytes_unchanged'] or not all(x['bytes_unchanged'] for x in settings['files']):
        raise ValueError('Local authentication or route configuration changed')
    for name in ('development-preflight-01.json','development-preflight-02.json'):
        check=read(name)
        if check['environment_executed'] or check['scored']:raise ValueError('Diagnostic was scored')
    if (ROOT/'trajectories.html').read_text(encoding='utf-8')!=render(data):
        raise ValueError('Readable report differs')
    print('Verified complete continuous attempt, opaque-state commitments, public input projections and business regrading.')


if __name__=='__main__':main()
