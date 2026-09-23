"""Continuous native tool dialogue; opaque reasoning stays in process memory."""
import copy
import hashlib
import json

from .model_io import AdapterError, NATIVE_TOOLS


def fingerprint(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def public_items(items):
    """Retain a verifiable projection, never encrypted or plaintext reasoning."""
    result = copy.deepcopy(items)
    for item in result:
        if item.get('type') == 'reasoning':
            encrypted = item.pop('encrypted_content', None)
            summary = item.pop('summary', [])
            item['encrypted_content_sha256'] = fingerprint(encrypted)
            item['summary_sha256'] = fingerprint(summary)
    return result


def projected_payload(payload):
    return {**payload, 'input': public_items(payload['input'])}


class NativeSession:
    def __init__(self):
        self.items = []
        self.history_hash = fingerprint([])
        self.turns = 0
        self.pending = None
        self.call_ids = set()
        self.task_hash = None

    def request(self, config, request):
        if set(request) != {'protocol_version', 'task', 'observation', 'history'}:
            raise AdapterError('Invalid public request projection', 'configuration_error')
        history = request['history']
        if len(history) != self.turns:
            raise AdapterError('Native session history is discontinuous', 'protocol_error')
        if not self.items:
            self.task_hash = fingerprint(request['task'])
            self.items.append({'role':'user', 'content':json.dumps(request, ensure_ascii=False, allow_nan=False)})
        else:
            if (self.pending is None or fingerprint(request['task']) != self.task_hash
                    or fingerprint(history[:-1]) != self.history_hash
                    or history[-1]['action'] != self.pending['action']
                    or history[-1]['observation'] != request['observation']):
                raise AdapterError('Native session action/result binding changed', 'protocol_error')
            self.items.append({'type':'function_call_output','call_id':self.pending['call_id'],
                               'output':json.dumps(request['observation'], ensure_ascii=False, allow_nan=False)})
            self.history_hash = fingerprint(history)
            self.pending = None
        options = copy.deepcopy(config.get('options', {}))
        if 'reasoning_effort' in options:
            options['reasoning'] = {'effort':options.pop('reasoning_effort')}
        return {'model':config['model'], **options,
                'instructions':'Follow the task contract. Use the provided tools to act.',
                'input':copy.deepcopy(self.items), 'tools':copy.deepcopy(NATIVE_TOOLS),
                'tool_choice':'required','parallel_tool_calls':False,'store':False,'stream':True,
                'include':['reasoning.encrypted_content']}

    def accept(self, data, action, audit):
        items = []
        try:
            for item in data['output']:
                kind = item['type']
                if kind == 'reasoning':
                    if not isinstance(item.get('encrypted_content'), str) or not item['encrypted_content']:
                        raise AdapterError('Endpoint omitted encrypted reasoning continuity', 'missing_reasoning_state')
                    fields = ('type','id','encrypted_content','summary')
                elif kind == 'message':
                    if item.get('role') != 'assistant':
                        raise ValueError()
                    fields = ('type','id','status','role','phase','content')
                elif kind == 'function_call':
                    identity = item['call_id']
                    if not isinstance(identity, str) or not identity or identity in self.call_ids:
                        raise ValueError()
                    fields = ('type','id','status','call_id','name','arguments')
                else:
                    raise ValueError()
                items.append({key:copy.deepcopy(item[key]) for key in fields if key in item})
            calls = [item for item in items if item['type']=='function_call']
            if len(calls) != 1:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise AdapterError('Invalid native continuation items', 'protocol_error') from None
        identity = calls[0]['call_id']
        self.call_ids.add(identity)
        self.items.extend(items)
        self.pending = {'call_id':identity,'action':copy.deepcopy(action)}
        self.turns += 1
        audit.update(response_items=public_items(items), response_items_sha256=fingerprint(items),
                     preserved_reasoning_items=sum(item['type']=='reasoning' for item in items))
