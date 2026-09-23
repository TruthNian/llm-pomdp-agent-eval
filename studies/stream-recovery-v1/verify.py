"""Regrade retained observations and reconstruct every public-only model request."""
import hashlib
import html
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.model_io import request_body

ROOT = Path(__file__).resolve().parent
CONTROLS = ['untouched', 'restore_tables_only', 'blind_replay', 'preserve_reconcile']


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def render(data):
    esc = lambda value: html.escape(str(value))
    block = lambda value: '<pre>'+esc(json.dumps(value, ensure_ascii=False, indent=2))+'</pre>'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>事故恢复：完整轨迹与业务验收</title><style>'
             'body{margin:0;background:#eef2f5;color:#172f43;font:16px/1.65 system-ui}'
             'main{max-width:1050px;margin:30px auto;padding:0 18px}'
             'section{background:white;border:1px solid #cbd6df;border-radius:10px;padding:22px;margin:18px 0}'
             'pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:650px;overflow:auto;'
             'background:#f3f6f8;padding:14px;font:12px/1.55 monospace}summary{cursor:pointer;color:#175987}'
             'h1{font-size:28px}h2{font-size:21px}</style><main><h1>事故恢复：完整轨迹与业务验收</h1>'
             '<p>保留实际动作、反馈和终止后的独立业务观察。脚本对照用于检查机制与可解性，不能充当模型分数。'
             '这里复核已记录行为，不声称实时环境可逐字重执行，也不把单个构造事故推广为普遍高难度。</p>']
    for record in data['records']:
        status = '已交付' if record['grade']['success'] else '未交付'
        parts.append('<section><h2>'+esc(record['agent']['name'])+' · '+status+'</h2>'
                     +block({k:record.get(k) for k in ('grade','elapsed_seconds','error','agent','usage')})
                     +'<details><summary>最初的任务与观察</summary>'
                     +block({k:record[k] for k in ('contract','initial_observation')})+'</details></section>')
        for index,event in enumerate(record['events'],1):
            parts.append('<section><h2>动作 '+str(index)+'</h2>'+block(event['action'])
                         +'<details><summary>实际反馈</summary>'+block(event['observation'])+'</details></section>')
        private = [call for call in record['service_evidence']['calls']
                   if call['response'].get('audit') is not None or call['response'].get('audit_error')]
        parts.append('<section><details><summary>独立业务验收（未反馈给模型）</summary>'+block(private)
                     +'</details><details><summary>请求与工具身份审计</summary>'
                     +block(record.get('request_audit',[]))+'</details></section>')
    parts.append('<p>冻结采集源码：'+esc(data['git_revision'])+'</p></main></html>\n')
    return ''.join(parts)


def main():
    plan,execution = read('plan.json'),read('execution.json')
    required = {'plan.json','README.md','model-evidence.json','control-evidence.json',
                'trajectories.html','controls.html','verify.py',
                'controls/restore.sh','controls/reconcile.sh','../../tools/qualify_stream.py'}
    if not required <= execution['file_sha256'].keys():
        raise ValueError('Missing published evidence binding')
    for name,expected in execution['file_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('Published bytes changed: '+name)
    shared = None
    for filename,report,model in [('control-evidence.json','controls.html',False),
                                  ('model-evidence.json','trajectories.html',True)]:
        data = read(filename)
        names = [a['name'] for a in plan['agents']] if model else CONTROLS
        if (data['git_revision']!=execution['source_commit'] or data['working_tree_dirty']
                or data['expected']!=len(names) or data['retained']!=len(names)
                or sorted(r['agent']['name'] for r in data['records'])!=sorted(names)
                or len(data['cases'])!=1):
            raise ValueError('Incomplete or unfrozen matrix')
        if digest({'generator_version':plan['generator_version'],'cases':data['cases']})!=plan['suite_sha256']:
            raise ValueError('Suite changed')
        if shared is not None and data['source_sha256']!=shared:
            raise ValueError('Model/control sources differ')
        shared = data['source_sha256']
        if any(shared.get(k)!=v for k,v in plan['environment_source_sha256'].items()):
            raise ValueError('Qualified environment changed')
        if model:
            settings = data['settings_check']
            if (not settings['settings_and_auth_bytes_unchanged']
                    or not all(item['bytes_unchanged'] for item in settings['files'])):
                raise ValueError('Local route configuration changed')
        for record in data['records']:
            grade = replay(record,data['cases'][0])
            if (record['framework_version']!=plan['framework_version']
                    or record['condition']!='open' or record['replicate']!=0):
                raise ValueError('Episode contract changed')
            if model:
                if record['agent'] not in plan['agents']:
                    raise ValueError('Model configuration changed')
                for index,audit in enumerate(record['request_audit']):
                    history = record['events'][:index]
                    request = {'protocol_version':1,'task':record['contract'],
                               'observation':history[-1]['observation'] if history else record['initial_observation'],
                               'history':history}
                    raw = json.dumps(request_body(record['agent'],request),ensure_ascii=False,allow_nan=False).encode()
                    if (hashlib.sha256(raw).hexdigest()!=audit['request_sha256']
                            or audit['declared_tools']!=['exec','finish'] or audit['tool_choice']!='required'
                            or audit['max_response_bytes']!=record['agent']['max_response_bytes']):
                        raise ValueError('Public-only native request does not reproduce')
            elif (record['error'] or grade['observer_errors']
                  or grade['success']!=(record['agent']['name']=='preserve_reconcile')):
                raise ValueError('Qualification failed')
            for call in record['service_evidence']['calls']:
                audit = call['response'].get('audit')
                if audit and (audit['image']!=plan['runtime']['image']
                              or audit['components']!=plan['runtime']['components']):
                    raise ValueError('Runtime changed')
        if (ROOT/report).read_text(encoding='utf-8')!=render(data):
            raise ValueError('Report differs from recorded evidence')
    print('Verified four controls, complete model retention, public-only requests and business regrading.')


if __name__=='__main__':
    main()
