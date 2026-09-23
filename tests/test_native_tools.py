import copy
import json
import unittest
from unittest.mock import patch

from pomdp_bench.agents import validate_agent_version,validate_config
from pomdp_bench.collection import validate_definition
from pomdp_bench.evaluation import run_episode,replay
from pomdp_bench.generator import suite as diagnostic_suite
from pomdp_bench.model_io import AdapterError,ResponseStream,action_text,request_body
from pomdp_bench.takeover import make_case,suite
from tests.test_model_io import config,endpoint,send,sse
from tests.test_takeover import audit


def call(name='exec', arguments=None):
    return {'type':'function_call','id':'fc_1','call_id':'call_1','name':name,
            'arguments':json.dumps(arguments if arguments is not None else {'target':'printf hello'})}


def envelope(item=None):
    return {'status':'completed','model':'test-model','output':[
        {'type':'message','status':'completed','role':'assistant','content':[{'type':'output_text','text':'I will inspect the workspace.'}]},
        item or call()], 'usage':{'input_tokens':12,'output_tokens':7}}


def stream(item=None,terminal=None):
    item=item or call()
    return b''.join(sse(event) for event in [
        {'type':'response.output_item.added','output_index':0,'item':{**item,'arguments':''}},
        {'type':'response.function_call_arguments.delta','output_index':0,'item_id':item['id'],'delta':item['arguments']},
        {'type':'response.function_call_arguments.done','output_index':0,'item_id':item['id'],'arguments':item['arguments']},
        {'type':'response.output_item.done','output_index':0,'item':item},
        {'type':'response.completed','response':terminal or {'status':'completed','model':'test-model','output':[]}},
    ])


class NativeToolTests(unittest.TestCase):
    def test_request_and_family_scope(self):
        cfg=config('responses_tools')
        validate_config(cfg)
        public={'task':{'task':'public'},'observation':{},'history':[]}
        body=request_body(cfg,public)
        self.assertEqual([x['name'] for x in body['tools']],['exec','finish'])
        self.assertEqual(body['tool_choice'],'required')
        self.assertFalse(body['parallel_tool_calls'])
        self.assertFalse(body['store'])
        self.assertEqual(json.loads(body['input'][0]['content']),public)
        self.assertNotIn('previous_response_id',body)
        validate_definition(suite(),[cfg],['open'],1,100)
        with self.assertRaises(ValueError):validate_definition(diagnostic_suite([1]),[cfg],['open'],1,100)
        with self.assertRaises(ValueError):validate_agent_version(cfg,'2.13.0')

    def test_only_explicit_call_acts(self):
        self.assertEqual(action_text(envelope(),'responses_tools'),{'command':'exec','target':'printf hello'})
        self.assertEqual(action_text(envelope(call('finish',{})),'responses_tools'),{'command':'finish'})
        data=envelope();data['output'][0]['content'][0]['text']='{"command":"finish"}'
        self.assertEqual(action_text(data,'responses_tools')['command'],'exec')
        with self.assertRaises(AdapterError):action_text(data,'responses')

    def test_ambiguous_undeclared_malformed_and_incomplete_calls_do_not_act(self):
        variants=[]
        data=envelope();data['output'].append(call());variants.append(data)
        data=envelope();data['output']=data['output'][:1];variants.append(data)
        data=envelope();data['status']='in_progress';variants.append(data)
        for item in (call('delete_host',{}),call('finish',{'target':'anything'}),call('exec',{'target':9}),
                     call('exec',{'target':'hello','extra':True}),{**call(),'arguments':'not json'},
                     {**call(),'status':'in_progress'},{'type':'web_search_call'}):
            variants.append(envelope(item))
        for data in variants:
            with self.subTest(data=data),self.assertRaises(AdapterError):action_text(data,'responses_tools')

    def test_stream_closure_and_terminal_call_binding(self):
        parser=ResponseStream(('exec','finish'))
        raw=stream()
        for byte in raw:parser.feed(bytes([byte]))
        parser.feed(b'',final=True)
        self.assertEqual(action_text(parser.result,'responses_tools')['target'],'printf hello')
        with self.assertRaises(AdapterError):ResponseStream().feed(raw)
        changed={'status':'completed','output':[call('exec',{'target':'different'})]}
        with self.assertRaises(AdapterError):ResponseStream(('exec','finish')).feed(stream(terminal=changed))
        parser=ResponseStream(('exec','finish'))
        parser.feed(sse({'type':'response.output_item.added','output_index':0,'item':call()}))
        with self.assertRaises(AdapterError):parser.feed(sse({'type':'response.completed','response':{'status':'completed','output':[]}}))

    def test_function_identity_cannot_change_or_cross_items(self):
        parser=ResponseStream(('exec','finish'))
        parser.feed(sse({'type':'response.output_item.added','output_index':0,'item':call()}))
        with self.assertRaises(AdapterError):parser.feed(sse({'type':'response.output_item.done','output_index':0,'item':call('finish',{})}))
        parser=ResponseStream(('exec','finish'))
        with self.assertRaises(AdapterError):parser.feed(sse({'type':'response.function_call_arguments.delta','item_id':'unknown','output_index':0,'delta':'{}'}))
        parser=ResponseStream(('exec','finish'))
        parser.feed(sse({'type':'response.output_item.added','output_index':0,'item':call()}))
        parser.feed(sse({'type':'response.function_call_arguments.done','item_id':'fc_1','output_index':0,'arguments':'{}'}))
        with self.assertRaises(AdapterError):parser.feed(sse({'type':'response.output_item.done','output_index':0,'item':call()}))

    def test_complete_http_episode_uses_public_history_and_no_host_execution(self):
        actions=[]
        class FakeRuntime:
            def __init__(self,case):pass
            def close(self):pass
            def call(self,action):
                actions.append(copy.deepcopy(action))
                return {'result':{'handover':True} if action['command']=='finish' else {'exit_code':0,'output':'hello'},
                        'audit':audit() if action['command']=='finish' else None,'state_sha256':None}
        def reply(handler,body):
            public=json.loads(body['input'][0]['content'])
            self.assertNotIn('initial_receipts',json.dumps(public))
            item=call('finish',{}) if public['history'] else call()
            send(handler,stream(item),'text/event-stream')
        with endpoint(reply) as received,patch('pomdp_bench.takeover.Runtime',FakeRuntime):
            result=run_episode(make_case(),config('responses_tools'),'open',0)
        self.assertTrue(result['grade']['success'])
        self.assertTrue(replay(result,make_case())['success'])
        self.assertEqual(actions,[{'command':'exec','target':'printf hello'},{'command':'finish'}])
        self.assertEqual(len(received),2)
        self.assertTrue(all(x['declared_tools']==['exec','finish'] for x in result['request_audit']))


if __name__ == '__main__':unittest.main()
