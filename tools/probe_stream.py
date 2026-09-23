"""Retain one development artifact execution; never calls a model or retries it."""
import argparse
import json
from pathlib import Path
import time
import traceback

from pomdp_bench.stream_runtime import Runtime, assess, asset_hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--script',action='append',type=Path,default=[])
    parser.add_argument('--no-traffic',action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    data = {'kind':'development artifact control, not a model attempt','asset_sha256':asset_hashes(),
            'traffic_enabled':not args.no_traffic,'events':[],'status':'starting'}
    runtime = None
    def progress(value):
        print(value,flush=True)
        with (args.output/'progress.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'elapsed':time.monotonic()-started,'message':value})+'\n')
    try:
        runtime = Runtime(progress=progress,traffic=not args.no_traffic)
        data.update(runtime_image=runtime.image,initial_provenance=runtime.provenance)
        for path in args.script:
            progress('Executing declared artifact '+path.name)
            action = {'command':'exec','target':path.read_text(encoding='utf-8')}
            response = runtime.call(action)
            data['events'].append({'action':action,'response':response})
            (args.output/'partial.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        progress('Independent terminal business observations')
        response = runtime.call({'command':'finish'})
        data['events'].append({'action':{'command':'finish'},'response':response})
        data['grade'] = assess(response['audit'])
        data['status'] = 'audit_error' if response.get('audit_error') else 'completed'
        data['terminal_diagnostics'] = runtime.shell("python3 - <<'PY'\nimport json,subprocess\nfrom pathlib import Path\nresult={}\nfor command in (['supervisorctl','status'],['curl','-sS','--max-time','5','http://127.0.0.1:8083/connectors?expand=status'],['psql','-h','127.0.0.1','-p','5433','-U','postgres','-d','commerce','-x','-c','SELECT slot_name,active,restart_lsn,confirmed_flush_lsn FROM pg_replication_slots; SELECT count(*),max(id) FROM outbox;']):\n p=subprocess.run(command,capture_output=True,text=True,timeout=10);result[' '.join(command)]={'code':p.returncode,'out':p.stdout,'err':p.stderr}\nfor name in ('connect','dispatch','broker'):\n p=Path('/var/log/commerce')/(name+'.log');result[name]=p.read_text()[-24000:] if p.exists() else None\nprint(json.dumps(result))\nPY")
        print(json.dumps({'status':data['status'],'grade':data['grade']}),flush=True)
    except Exception as exc:
        data.update(status='execution_error',error=type(exc).__name__,detail=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        if runtime:
            runtime.close()
        data['elapsed_seconds'] = time.monotonic()-started
        (args.output/'evidence.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
