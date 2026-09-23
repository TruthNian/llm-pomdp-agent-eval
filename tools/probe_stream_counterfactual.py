"""Matched post-hoc artifact execution; never calls or advises a model."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback

from pomdp_bench.collection import source_hashes
from pomdp_bench.stream_runtime import Runtime, assess, configuration

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'studies/stream-recovery-counterfactual-v1'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('arm',choices=('original','restore_missing'))
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    plan=json.loads((STUDY/'plan.json').read_text())
    path=STUDY/plan['source_study']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=plan['source_evidence_sha256']:
        raise ValueError('Original model evidence changed')
    original=json.loads(path.read_text())['records'][0]
    config=configuration()
    if any(config.get(k)!=v for k,v in plan['runtime'].items()):
        raise ValueError('Runtime changed')
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('Freeze the counterfactual before executing')
    args.output.mkdir(parents=True,exist_ok=False)
    data={'kind':'post-hoc artifact counterfactual; no model calls','arm':args.arm,
          'plan_sha256':hashlib.sha256((STUDY/'plan.json').read_bytes()).hexdigest(),
          'source_sha256':source_hashes(),'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
          'events':[],'exit_code_mismatches':[],'status':'starting'}
    started=time.monotonic()
    runtime=None
    def progress(message):
        print(message,flush=True)
        with (args.output/'progress.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'elapsed':time.monotonic()-started,'message':message})+'\n')
    def act(action):
        response=runtime.call(action)
        data['events'].append({'action':action,'response':response})
        (args.output/'partial.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        return response
    try:
        runtime=Runtime(progress=progress,traffic=False)
        for bodies in plan['preloaded_customer_batches']:
            records=runtime.submit(bodies)
            runtime.traffic.append({'elapsed':round(time.monotonic()-runtime.started,6),'commands':records})
            if any(x['response'].get('status')!=201 for x in records):
                raise RuntimeError('Matched customer batch was not accepted')
        for number,event in enumerate(original['events'],1):
            if event['action']['command']=='finish':
                break
            if str(number) in plan['settle_seconds_before_actions']:
                progress('Declared settling pause before action '+str(number))
                time.sleep(plan['settle_seconds_before_actions'][str(number)])
            progress('Original model action '+str(number))
            observed=act(event['action'])['result']
            expected=event['observation']['result']
            fields=('exit_code','timed_out','output_truncated')
            if any(observed.get(k)!=expected.get(k) for k in fields):
                data['exit_code_mismatches'].append({'action':number,
                    'expected':{k:expected.get(k) for k in fields},'observed':{k:observed.get(k) for k in fields}})
        if args.arm=='restore_missing':
            for script in (ROOT/'studies/stream-recovery-v1/controls/restore.sh',STUDY/'restore-missing.sh'):
                progress('Declared data-only intervention '+script.name)
                result=act({'command':'exec','target':script.read_text()})['result']
                if result.get('exit_code') or result.get('timed_out'):
                    raise RuntimeError('Data-only recovery command failed')
        progress('Independent business audit')
        response=act({'command':'finish'})
        data.update(grade=assess(response['audit']),status='completed' if not response.get('audit_error') else 'audit_error')
        print(json.dumps({'arm':args.arm,'grade':data['grade'],'exit_code_mismatches':data['exit_code_mismatches']}),flush=True)
    except Exception as exc:
        data.update(status='execution_error',error=type(exc).__name__,detail=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        if runtime:runtime.close()
        data['elapsed_seconds']=time.monotonic()-started
        (args.output/'evidence.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
