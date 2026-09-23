import copy
import json
import unittest
from unittest.mock import patch

from pomdp_bench.agents import validate_agent_version, validate_config
from pomdp_bench.collection import validate_definition
from pomdp_bench.evaluation import run_episode, replay
from pomdp_bench.model_io import AdapterError, ResponseStream
from pomdp_bench.native_session import NativeSession, fingerprint, projected_payload
from pomdp_bench.stream import suite as stream_suite
from pomdp_bench.takeover import make_case
from tests.test_model_io import config, endpoint, send, sse
from tests.test_native_tools import call
from tests.test_takeover import audit


def output(number=1, finish=False):
    return [
        {'type':'reasoning','id':f'rs_{number}','summary':[],
         'encrypted_content':f'OPAQUE_NOT_FOR_PUBLICATION_{number}'},
        {'type':'message','id':f'msg_{number}','role':'assistant','status':'completed','phase':'commentary',
         'content':[{'type':'output_text','text':'Inspecting the available evidence.','annotations':[]}]},
        {**call('finish' if finish else 'exec', {} if finish else {'target':'printf hello'}),
         'id':f'fc_{number}','call_id':f'call_{number}'}]


def stream(items, terminal=None):
    events=[]
    for index,item in enumerate(items):
        events += [{'type':'response.output_item.added','output_index':index,'item':item},
                   {'type':'response.output_item.done','output_index':index,'item':item}]
    events.append({'type':'response.completed','response':terminal or
                   {'status':'completed','model':'test-model','output':[],
                    'usage':{'input_tokens':12,'output_tokens':7}}})
    return b''.join(sse(event) for event in events)


class NativeSessionTests(unittest.TestCase):
    def test_version_and_incident_scope(self):
        cfg=config('responses_session')
        validate_config(cfg)
        validate_agent_version(cfg,'2.16.0')
        validate_definition(stream_suite(),[cfg],['open'],1,100)
        with self.assertRaises(ValueError):validate_agent_version(cfg,'2.15.0')

    def test_empty_terminal_keeps_opaque_reasoning_but_old_mode_is_unchanged(self):
        for preserve in (False,True):
            parser=ResponseStream(('exec','finish'),preserve_reasoning=preserve)
            parser.feed(stream(output()));parser.feed(b'',final=True)
            self.assertEqual('encrypted_content' in parser.result['output'][0],preserve)
        terminal={'status':'completed','output':output()}
        terminal['output'][0]['encrypted_content']='changed'
        with self.assertRaises(AdapterError):
            ResponseStream(('exec','finish'),preserve_reasoning=True).feed(stream(output(),terminal))

    def test_complete_dialogue_preserves_state_phase_and_call_identity_without_publishing_reasoning(self):
        actions=[]
        class FakeRuntime:
            def __init__(self,case):pass
            def close(self):pass
            def call(self,action):
                actions.append(copy.deepcopy(action))
                return {'result':{'handover':True} if action['command']=='finish' else {'exit_code':0,'output':'hello'},
                        'audit':audit() if action['command']=='finish' else None,'state_sha256':None}
        count=0
        def reply(handler,body):
            nonlocal count
            count+=1
            self.assertEqual(body['include'],['reasoning.encrypted_content'])
            self.assertNotIn('initial_receipts',json.dumps(body))
            if count==1:
                self.assertEqual(len(body['input']),1)
                self.assertEqual(json.loads(body['input'][0]['content'])['history'],[])
            else:
                self.assertEqual(body['input'][1:4],output())
                result=body['input'][4]
                self.assertEqual((result['type'],result['call_id']),('function_call_output','call_1'))
                self.assertEqual(json.loads(result['output'])['result']['output'],'hello')
                self.assertEqual(body['input'][2]['phase'],'commentary')
            send(handler,stream(output(count,finish=count==2)),'text/event-stream')
        with endpoint(reply) as received,patch('pomdp_bench.takeover.Runtime',FakeRuntime):
            record=run_episode(make_case(),config('responses_session'),'open',0)
        self.assertTrue(record['grade']['success'],record['error'])
        self.assertTrue(replay(record,make_case())['success'])
        self.assertEqual(len(received),2)
        received=[json.loads(raw) for raw,headers in received]
        self.assertNotIn('OPAQUE_NOT_FOR_PUBLICATION',json.dumps(record))
        self.assertEqual([x['preserved_reasoning_items'] for x in record['request_audit']],[1,1])
        for body,entry in zip(received,record['request_audit']):
            self.assertEqual(fingerprint(projected_payload(body)),entry['input_projection_sha256'])
        # Anyone can rebuild the public input projection without the opaque state.
        projected=projected_payload(received[0])
        projected['input'].extend(record['request_audit'][0]['response_items'])
        projected['input'].append(received[1]['input'][-1])
        self.assertEqual(fingerprint(projected),record['request_audit'][1]['input_projection_sha256'])

    def test_missing_encrypted_state_never_silently_downgrades_to_stateless(self):
        session=NativeSession()
        items=output();items[0].pop('encrypted_content')
        with self.assertRaisesRegex(AdapterError,'encrypted'):
            session.accept({'output':items},{'command':'exec','target':'printf hello'}, {})
        self.assertEqual(session.items,[])

    def test_changed_public_history_and_reused_call_identity_are_rejected(self):
        cfg=config('responses_session')
        request={'protocol_version':1,'task':{'task':'public'},'observation':{'result':'start'},'history':[]}
        session=NativeSession();session.request(cfg,request)
        action={'command':'exec','target':'printf hello'}
        session.accept({'output':output()},action,{})
        event={'action':action,'observation':{'result':'hello'}}
        follow={**request,'history':[event],'observation':event['observation']}
        changed=copy.deepcopy(follow);changed['history'][0]['action']['target']='different'
        with self.assertRaises(AdapterError):session.request(cfg,changed)
        session.request(cfg,follow)
        with self.assertRaises(AdapterError):session.accept({'output':output()},action,{})
        another=NativeSession()
        with self.assertRaises(AdapterError):another.request(cfg,follow)
        with self.assertRaises(AdapterError):NativeSession().request(cfg,{**request,'private_seed':42})


if __name__=='__main__':unittest.main()
