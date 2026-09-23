"""Export and review complete versioned service studies; never calls a model."""
import argparse
import hashlib
import html
import json
from pathlib import Path

from pomdp_bench.collection import read_run, source_hashes
from pomdp_bench.evaluation import replay
from pomdp_bench.generator import digest
from pomdp_bench.storage import read_json
from pomdp_bench.worlds import Environment


def write(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def export(directory, output):
    manifest, records = read_run(directory)
    if source_hashes() != manifest['source_sha256']:
        raise ValueError('Use the frozen collection package for fresh execution')
    cases = {digest(c): c for c in manifest['cases']}
    states, errors = [], []
    for record in records:
        env = Environment(cases[record['case_id']], framework_version=record['framework_version'])
        runtime = env.make_runtime()
        try:
            for call in record['service_evidence']['calls']:
                if runtime.call(call['action']) != call['response']:
                    raise ValueError('Fresh execution disagrees with recorded response')
            states.append({'agent': record['agent']['name'], 'case_id': record['case_id'],
                           'kind': 'fresh reexecution matched' if record['events'] else 'initial reconstruction only; original runtime never created',
                           'tables': runtime.tables()})
        except (ValueError, RuntimeError) as exc:
            errors.append({'case_id': record['case_id'], 'error': str(exc)})
        finally:
            runtime.close()
    data = {key: manifest[key] for key in ('git_revision', 'working_tree_dirty', 'source_sha256', 'suite_sha256', 'cases')}
    data.update(expected=manifest['expected_episodes'], retained=len(records), records=records,
                settings_check=read_json(directory/'private/settings-check.json'),
                fresh_recheck_errors=errors, fresh_final_states=states)
    write(output, data)
    if errors:
        raise SystemExit('Fresh disagreements retained')
    print({'retained': len(records), 'accepted': sum(r['grade']['success'] for r in records), 'fresh_disagreements': 0})


def render(data):
    esc = lambda v: html.escape(str(v))
    block = lambda v: '<pre>'+esc(json.dumps(v, ensure_ascii=False, indent=2))+'</pre>'
    rows, sections = [], []
    for n, record in enumerate(data['records'], 1):
        grade = record['grade']
        label = record['agent']['name']+' / '+record['profile']
        model = record['agent']['kind'] in ('responses', 'chat')
        status = '已交付' if grade['success'] else '未交付（接入错误）' if record.get('error') else '未交付'
        elapsed = f"{record['elapsed_seconds']:.1f} 秒" if model else '未测量（脚本）'
        rows.append(f'<tr><td><a href="#e{n}">{esc(label)}</a></td><td>{status}</td><td>{grade["steps"]}/{grade["budget"]}</td><td>{elapsed}</td></tr>')
        steps = []
        for i, (event, call) in enumerate(zip(record['events'], record['service_evidence']['calls']), 1):
            action = event['action']
            command = action.get('command', '无效动作') if isinstance(action, dict) else '无效动作'
            steps.append(f'<article><b>{i:02d} · {esc(command)}</b><details><summary>完整动作与模型实际收到的反馈</summary>'+block(event)+'</details><details><summary>评测器观察（未随动作反馈提供给模型）</summary>'+block(call['response']['audit'])+'</details></article>')
        state = next((s for s in data.get('fresh_final_states', []) if s['agent'] == record['agent']['name'] and s['case_id'] == record['case_id']), None)
        sections.append(f'<section id="e{n}"><h2>{esc(label)}</h2><p>{status} · {grade["steps"]} 步 · {elapsed}</p>'
                        +('<p class="warning">'+esc(record['error'])+'</p>' if record.get('error') else '')
                        +'<details><summary>验收、模型配置、用量及每次请求的身份审计</summary>'+block({k:record.get(k) for k in ('grade','agent','usage','request_audit')})+'</details>'
                        +'<details><summary>初始公开契约与观察</summary>'+block({k:record[k] for k in ('contract','initial_observation')})+'</details>'
                        +''.join(steps)+('<details><summary>新建服务重执行后的数据库与重建范围</summary>'+block(state)+'</details>' if state else '')+'</section>')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完整服务任务轨迹</title><style>
body{margin:0;background:#eef2f5;color:#182c3c;font:16px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:35px auto;padding:0 20px}h1{font-size:30px}h2{font-size:20px;overflow-wrap:anywhere}section{background:white;border:1px solid #ccd9e0;border-radius:10px;padding:24px;margin:24px 0}table{width:100%;border-collapse:collapse;text-align:left}td,th{padding:12px;border-bottom:1px solid #ddd}article{padding:15px 0;border-bottom:1px solid #ddd}summary{cursor:pointer;color:#17608b}pre{font:12px/1.6 ui-monospace,monospace;background:#f2f5f8;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:550px;overflow:auto}.scroll{overflow:auto}.warning{border:2px solid #a2681e;padding:12px}a{color:#17608b}@media(max-width:700px){main{padding:0 12px}section{padding:14px}td,th{padding:8px}}
</style><main><h1>完整任务轨迹与实际验收</h1><p>保留全部动作、SQL、反馈、失败和请求审计。脚本对照只验证机制；模型完成或失败必须单独判断。路由返回的模型名称不是权重认证。少量构造任务的结果不能证明普遍高难度。</p>'''+('<details><summary>配置与认证文件采集前后是否变化</summary>'+block(data['settings_check'])+'</details>' if 'settings_check' in data else '')+'<section><div class="scroll"><table><thead><tr><th>路由 / 对照</th><th>结果</th><th>动作</th><th>耗时</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'+''.join(sections)+'<p>冻结源码：'+esc(data['git_revision'])+'。新执行差异：'+esc(data['fresh_recheck_errors'])+'</p></main></html>\n'


def verify(root):
    execution, plan = read_json(root/'execution.json'), read_json(root/'plan.json')
    required = {'plan.json', 'model-evidence.json', 'trajectories.html', 'README.md', '../../tools/service_study.py'}
    if 'controls' in plan:
        required.update(('controls.py', 'control-evidence.json', 'controls.html'))
    if (not required <= execution['file_sha256'].keys() or plan['conditions'] != ['open']
            or plan['replicates'] != 1 or execution['model_episodes'] != plan['expected_episodes']):
        raise ValueError('Missing evidence binding or unsupported study matrix')
    for filename, expected in execution['file_sha256'].items():
        if hashlib.sha256((root/filename).read_bytes()).hexdigest() != expected:
            raise ValueError('Published bytes changed: '+filename)
    shared = None
    for filename in ('model-evidence.json', 'control-evidence.json'):
        if filename not in execution['file_sha256']:
            continue
        data = read_json(root/filename)
        model = filename.startswith('model')
        expected = ([(digest(c), a['name']) for c in data['cases'] for a in plan['agents']] if model else
                    [(digest(c), c['profile']+'/'+v) for c in data['cases'] for v in plan['controls']])
        if model and len(expected) != plan['expected_episodes']:
            raise ValueError('Preregistered model matrix count differs')
        if (data['expected'] != len(expected) or data['retained'] != len(expected)
                or len(data['records']) != len(expected) or data['working_tree_dirty']
                or data['git_revision'] != execution['source_commit'] or data['fresh_recheck_errors']
                or sorted(expected) != sorted((r['case_id'], r['agent']['name']) for r in data['records'])):
            raise ValueError('Incomplete or mismatched matrix/source')
        if digest({'generator_version':plan['generator_version'], 'cases':data['cases']}) != plan['suite_sha256']:
            raise ValueError('Suite changed')
        if shared is not None and shared != data['source_sha256']:
            raise ValueError('Control/model source differs')
        shared = data['source_sha256']
        for record in data['records']:
            case = next(c for c in data['cases'] if digest(c) == record['case_id'])
            replay(record, case)
            if record['framework_version'] != plan['framework_version'] or record['condition'] != 'open' or record['replicate'] != 0:
                raise ValueError('Version/episode settings differ')
            if model:
                if record['agent'] not in plan['agents']:
                    raise ValueError('Agent settings differ')
                state = next(s for s in data['fresh_final_states'] if s['agent'] == record['agent']['name'] and s['case_id'] == record['case_id'])
                calls = record['service_evidence']['calls']
                if calls and digest(state['tables']) != calls[-1]['response']['state_sha256']:
                    raise ValueError('Fresh final state changed')
            elif record['grade']['success'] != (record['agent']['name'].split('/')[-1] == 'complete'):
                raise ValueError('Control differs from specification')
        if model:
            settings = data['settings_check']
            if settings['settings_and_auth_bytes_unchanged'] != all(f['bytes_unchanged'] for f in settings['files']) or settings['settings_and_auth_bytes_unchanged'] != execution['settings_unchanged']:
                raise ValueError('Settings control changed')
            if not settings['settings_and_auth_bytes_unchanged']:
                print('Configuration invariance FAILED; do not treat as controlled comparison.')
        report = root/('trajectories.html' if model else 'controls.html')
        if report.read_text(encoding='utf-8') != render(data):
            raise ValueError('Report differs from evidence')
        print(f'Verified {len(expected)} complete records in {filename}; recorded replay only.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('export','render','verify'))
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    args = parser.parse_args()
    if args.mode == 'verify':
        verify(args.input)
    elif args.output is None:
        parser.error('export/render require output')
    elif args.mode == 'export':
        export(args.input, args.output)
    else:
        args.output.write_text(render(read_json(args.input)), encoding='utf-8', newline='\n')
