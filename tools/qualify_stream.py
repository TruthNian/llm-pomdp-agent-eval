"""Freeze and execute four declared artifact controls through the real collector."""
import argparse
import json
from pathlib import Path
import subprocess

from pomdp_bench.collection import prepare_suite, resume_suite
from pomdp_bench.stream import suite
from pomdp_bench.storage import write_json


def configs():
    root=Path(__file__).resolve().parents[1]/'studies/stream-recovery-v1/controls'
    restore=(root/'restore.sh').read_text(encoding='utf-8')
    reconcile=(root/'reconcile.sh').read_text(encoding='utf-8')
    result=[]
    for name,mode in [('untouched',None),('restore_tables_only','tables_only'),
                      ('blind_replay','blind_replay'),('preserve_reconcile','preserve')]:
        actions=[] if mode is None else [{'command':'exec','target':restore},
                    {'command':'exec','target':'export STREAM_CONTROL_MODE='+mode+'\n'+reconcile}]
        actions.append({'command':'finish'})
        result.append({'name':name,'kind':'actions','actions':actions})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('Commit source and declared controls before qualification')
    manifest=prepare_suite(suite(),configs(),['open'],1,args.output,1800)
    report=resume_suite(args.output)
    print(json.dumps({'episodes':report['episodes'],'complete':report['complete']}))


if __name__=='__main__':
    main()
