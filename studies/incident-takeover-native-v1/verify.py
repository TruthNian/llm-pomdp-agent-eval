"""Regrade the retained native-tool episode and reproduce its public requests."""
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


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def render(data):
    record=data['records'][0]
    block=lambda obj:'<pre>'+html.escape(json.dumps(obj,ensure_ascii=False,indent=2))+'</pre>'
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>原生工具事故接手：完整轨迹</title><style>body{font:16px/1.65 system-ui;background:#eef2f5;color:#172f43;margin:0}'
           'main{max-width:1050px;margin:30px auto;padding:0 18px}section{background:white;border:1px solid #cbd6df;border-radius:10px;padding:24px;margin:20px 0}'
           'pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:650px;overflow:auto;background:#f3f6f8;padding:14px;font:12px/1.55 monospace}'
           'summary{cursor:pointer;color:#175987}h1{font-size:28px}h2{font-size:20px}</style><main><h1>原生工具事故接手：完整轨迹</h1>',
           '<p>Sol max 在 9/150 个动作内交付，110 笔已接受订单全部保留，重启后通过。按照运行前冻结的规则，此候选不再作为高难度证据。</p>'
           '<p>过程中发生 17 次读失败和 17 次写失败；业务契约允许短时维护。第 4、5 步普通命令出错，模型自行恢复，评估者没有提示或救场。</p>'
           '<p>记录重放与请求哈希复核；不声称实时环境逐字重执行。通道失败与事故决策失败分别判断。</p>',
           '<section><h2>'+('已交付' if record['grade']['success'] else '未交付')+'</h2>'+block({k:record[k] for k in ('grade','elapsed_seconds','error','usage','agent')})+'</section>',
           '<section><details><summary>模型初始收到的任务与观察</summary>'+block({k:record[k] for k in ('contract','initial_observation')})+'</details></section>']
    for number,event in enumerate(record['events'],1):
        parts.append('<section><h2>'+str(number)+' · '+html.escape(event['action'].get('command','invalid'))+'</h2>'+block(event['action'])+
                     '<details><summary>模型实际收到的原始输出</summary>'+block(event['observation'])+'</details></section>')
    parts.append('<section><details><summary>终止后的独立业务验收（未反馈模型）</summary>'+block(record['service_evidence']['calls'][-1]['response'])+'</details></section>')
    parts.append('<section><details><summary>每次请求的身份与工具声明审计</summary>'+block(record['request_audit'])+'</details></section></main></html>\n')
    return ''.join(parts)


def main():
    plan,data,execution=read('plan.json'),read('model-evidence.json'),read('execution.json')
    required={'plan.json','README.md','model-evidence.json','trajectories.html','preflight.json','verify.py'}
    if not required <= execution['file_sha256'].keys():raise ValueError('Missing evidence binding')
    for file,expected in execution['file_sha256'].items():
        if hashlib.sha256((ROOT/file).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('Published bytes changed: '+file)
    if (data['expected']!=1 or data['retained']!=1 or len(data['records'])!=1 or len(data['cases'])!=1
            or data['working_tree_dirty'] or data['git_revision']!=execution['source_commit']):
        raise ValueError('Unfrozen or incomplete native screen')
    settings=data['settings_check']
    if (not settings['settings_and_auth_bytes_unchanged']
            or not all(item['bytes_unchanged'] for item in settings['files'])):
        raise ValueError('Local route settings changed during collection')
    if digest({'generator_version':plan['generator_version'],'cases':data['cases']})!=plan['suite_sha256']:
        raise ValueError('Suite changed')
    if any(data['source_sha256'].get(k)!=v for k,v in plan['environment_source_sha256'].items()):
        raise ValueError('Qualified environment source changed')
    record=data['records'][0]
    replay(record,data['cases'][0])
    if record['agent']!=plan['agents'][0] or record['framework_version']!=plan['framework_version']:
        raise ValueError('Agent or framework changed')
    if (record['condition']!='open' or record['replicate']!=0 or record['error']
            or not record['grade']['success'] or record['grade']['steps']!=9
            or record['grade']['budget']!=150 or record['grade']['accepted_orders']!=110
            or record['grade']['traffic_read_failures']!=17 or record['grade']['traffic_write_failures']!=17
            or len(record['request_audit'])!=9):
        raise ValueError('Published outcome no longer supports the report')
    for index,audit in enumerate(record['request_audit']):
        history=record['events'][:index]
        request={'protocol_version':1,'task':record['contract'],
                 'observation':history[-1]['observation'] if history else record['initial_observation'],'history':history}
        raw=json.dumps(request_body(record['agent'],request),ensure_ascii=False,allow_nan=False).encode()
        if (hashlib.sha256(raw).hexdigest()!=audit['request_sha256'] or audit['declared_tools']!=['exec','finish']
                or audit['tool_choice']!='required' or audit['max_response_bytes']!=16000000):
            raise ValueError('Public-only native request does not reproduce')
    for call in record['service_evidence']['calls']:
        if call['response']['audit'] and call['response']['audit']['image']!=plan['runtime']['image']:
            raise ValueError('Image changed')
    preflight=read('preflight.json')
    if preflight['environment_executed'] or preflight['scored'] or not preflight['passed']:
        raise ValueError('Preflight was not a passing unscored protocol check')
    if (ROOT/'trajectories.html').read_text(encoding='utf-8')!=render(data):raise ValueError('Report changed')
    print('Verified one native-tool episode, public-only request hashes and independent business regrading.')


if __name__=='__main__':main()
