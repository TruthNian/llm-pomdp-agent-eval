"""Verify published bytes and regrade observations. Never claims fresh execution."""
import hashlib
import html
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from tools.service_study import render as render_base

ROOT = Path(__file__).resolve().parent


def render(data):
    body = render_base(data)
    terminal = []
    for record in data['records']:
        calls = record['service_evidence']['calls']
        if len(calls) > len(record['events']):
            terminal.append('<section><h2>中断后的独立业务观察（未反馈给模型）</h2><details><summary>'+html.escape(record['agent']['name'])+
                            '</summary><pre>'+html.escape(json.dumps(calls[len(record['events']):],ensure_ascii=False,indent=2))+'</pre></details></section>')
    return body.replace('</main>', ''.join(terminal)+'</main>')


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def main():
    execution, plan = read('execution.json'), read('plan.json')
    required = {'plan.json','README.md','model-evidence.json','control-evidence.json',
                'trajectories.html','controls.html','verify.py','../../tools/service_study.py'}
    if not required <= execution['file_sha256'].keys():
        raise ValueError('Missing published evidence binding')
    for path,expected in execution['file_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest() != expected:
            raise ValueError('Published evidence changed: '+path)
    shared = None
    for filename, report, model in (('model-evidence.json','trajectories.html',True),
                                     ('control-evidence.json','controls.html',False)):
        data = read(filename)
        if data['git_revision'] != execution['source_commit'] or data['working_tree_dirty']:
            raise ValueError('Unfrozen evidence')
        if digest({'generator_version':plan['generator_version'],'cases':data['cases']}) != plan['suite_sha256']:
            raise ValueError('Suite changed')
        expected_names = [a['name'] for a in plan['agents']] if model else plan['controls']
        if (len(data['cases']) != 1 or sorted(r['agent']['name'] for r in data['records']) != sorted(expected_names)
                or data['expected'] != len(expected_names) or data['retained'] != len(expected_names)):
            raise ValueError('Incomplete or unexpected matrix')
        if shared is not None and data['source_sha256'] != shared:
            raise ValueError('Control/model sources differ')
        shared = data['source_sha256']
        if model:
            settings = data['settings_check']
            if (settings['settings_and_auth_bytes_unchanged'] != all(x['bytes_unchanged'] for x in settings['files'])
                    or settings['settings_and_auth_bytes_unchanged'] != execution['settings_unchanged']):
                raise ValueError('Configuration invariance statement differs')
        for record in data['records']:
            grade = replay(record,data['cases'][0])
            if record['framework_version'] != plan['framework_version'] or record['condition'] != 'open' or record['replicate'] != 0:
                raise ValueError('Episode contract differs')
            if model and record['agent'] not in plan['agents']:
                raise ValueError('Agent configuration differs')
            if not model and (record['error'] or grade['observer_errors'] or grade['success'] != (record['agent']['name']=='preserve_and_merge')):
                raise ValueError('Qualification differs')
            for call in record['service_evidence']['calls']:
                audit = call['response']['audit']
                if audit and audit['image'] != plan['runtime']['image']:
                    raise ValueError('Runtime image differs')
        if (ROOT/report).read_text(encoding='utf-8') != render(data):
            raise ValueError('Readable report differs from evidence')
    if 'followup_source_commit' in execution:
        followup, extra = read('glm-followup-plan.json'), read('glm-evidence.json')
        if (extra['git_revision'] != execution['followup_source_commit'] or extra['working_tree_dirty']
                or extra['source_sha256'] != shared or extra['expected'] != 1 or extra['retained'] != 1
                or len(extra['records']) != 1 or extra['cases'] != data['cases']):
            raise ValueError('Follow-up changed the frozen source or matrix')
        record = extra['records'][0]
        replay(record,extra['cases'][0])
        if record['agent'] != followup['agents'][0] or record['framework_version'] != followup['framework_version']:
            raise ValueError('Follow-up agent changed')
        if digest({'generator_version':followup['generator_version'],'cases':extra['cases']}) != followup['suite_sha256']:
            raise ValueError('Follow-up suite changed')
        for call in record['service_evidence']['calls']:
            if call['response']['audit'] and call['response']['audit']['image'] != followup['runtime']['image']:
                raise ValueError('Follow-up image changed')
        hashes = {x['request_sha256'] for x in record.get('request_audit',[])}
        if any(x['request_sha256'] not in hashes for x in extra['response_shapes']):
            raise ValueError('Unbound response metadata')
        if (ROOT/'glm-trajectories.html').read_text(encoding='utf-8') != render(extra):
            raise ValueError('Follow-up report differs')
    print('Verified retained model attempts and four actual controls; recorded-behavior replay only.')


if __name__ == '__main__':
    main()
