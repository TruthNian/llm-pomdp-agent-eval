"""Same collector and adapter; retain response shape, never message/reasoning text."""
import hashlib
import json
from pathlib import Path
import sys

from pomdp_bench import model_io
from tools.collect_local_study import main

exchange = model_io.exchange


def observed_exchange(*args, **kwargs):
    data = exchange(*args, **kwargs)
    envelope = data if isinstance(data,dict) else {}
    allowed = {None,'message','reasoning','assistant','completed','in_progress','incomplete','failed',
               'final_answer','commentary','output_text','refusal'}
    def label(value):
        return value if isinstance(value,(str,type(None))) and value in allowed else 'other'
    row = {'request_sha256':hashlib.sha256(args[2]).hexdigest(), 'status':label(envelope.get('status')),
           'output':[]}
    items = envelope.get('output')
    for item in items if isinstance(items,list) else []:
        if not isinstance(item,dict):
            row['output'].append({'type':'other'})
            continue
        shape = {k:label(item.get(k)) for k in ('type','role','status','phase')}
        if item.get('type') == 'message':
            content = item.get('content')
            shape['parts'] = [{'type':label(p.get('type')),'text_length':len(p['text']) if isinstance(p.get('text'),str) else None}
                              for p in content if isinstance(p,dict)] if isinstance(content,list) else []
        row['output'].append(shape)
    with (Path(sys.argv[2])/'private/response-shapes.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    return data


if __name__ == '__main__':
    model_io.exchange = observed_exchange
    main()
