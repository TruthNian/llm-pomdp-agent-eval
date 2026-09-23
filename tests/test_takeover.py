import copy
import unittest
from unittest.mock import patch

from pomdp_bench.evaluation import episode_record, recover_interrupted, replay, replay_environment, run_episode
from pomdp_bench.takeover import TakeoverEnvironment, make_case
from pomdp_bench.takeover_runtime import assess, order
from pomdp_bench.worlds import Environment


def accepted(body, status=200):
    return {'status':status,'body':{'order_id':1,**copy.deepcopy(body)}}


def audit():
    initial = [order(i,1701) for i in range(90)]
    new = [order(i,1701) for i in range(10000,10006)]
    reads = [{'reference':x['reference'],'response':accepted(x)} for x in initial+new]
    return {'initial_orders':initial,'initial_receipts':[accepted(x,201) for x in initial],
            'traffic':[], 'new_writes':[{'order':x,'response':accepted(x,201)} for x in new],
            'reads':reads,'after_restart':copy.deepcopy(reads),
            'retries':[{'expected_status':200,'response':accepted(initial[0])},
                       {'expected_status':409,'response':{'status':409}}]}


class TakeoverTests(unittest.TestCase):
    def test_business_outcomes_and_receipts(self):
        self.assertTrue(assess(audit())['delivered'])
        damaged = audit()
        damaged['reads'][0]['response']['body']['items'][0]['quantity'] += 1
        self.assertEqual(assess(damaged)['missing_or_changed'],1)
        self.assertFalse(assess(damaged)['delivered'])
        damaged = audit()
        damaged['after_restart'][0]['response'] = {'status':404}
        self.assertEqual(assess(damaged)['post_restart_errors'],1)
        damaged = audit()
        damaged['retries'][0]['response']['body']['address'] = 'wrong'
        self.assertEqual(assess(damaged)['retry_errors'],1)

    def test_incomplete_evidence_rejected(self):
        for key in ('reads','after_restart','initial_orders','initial_receipts','new_writes','retries'):
            damaged = audit()
            damaged[key].pop()
            with self.assertRaises(ValueError):
                assess(damaged)

    def test_observer_failure_is_separate(self):
        damaged = audit()
        damaged['traffic']=[{'order':order(100,1701),'observer_error':'RuntimeError','responses':[{'status':None}]}]
        result=assess(damaged)
        self.assertFalse(result['delivered'])
        self.assertEqual(result['missing_or_changed'],0)
        self.assertEqual(result['observer_errors'],1)

    def test_private_audit_never_enters_observation_and_replay_regrades(self):
        env = TakeoverEnvironment(make_case())
        with patch.object(env,'start'):
            env.runtime = type('Fake',(),{'call':lambda _,action:{'result':{'handover':True},'audit':audit(),'state_sha256':None}})()
            observation = env.step({'command':'finish'})
        self.assertEqual(observation['result'],{'handover':True})
        self.assertNotIn('verification_current',observation)
        config={'name':'control','kind':'actions','actions':[{'command':'finish'}]}
        record=episode_record(env,config,0)
        self.assertTrue(replay(record,make_case())['success'])
        damaged=copy.deepcopy(record)
        damaged['service_evidence']['calls'][0]['response']['audit']['reads'][0]['response']={'status':404}
        with self.assertRaisesRegex(ValueError,'grade differs'):
            replay(damaged,make_case())
        with self.assertRaisesRegex(ValueError,'fresh run'):
            replay_environment(record,make_case(),execute_checks=True)

    def test_binding_and_interrupted_checkpoint(self):
        env=TakeoverEnvironment(make_case(),recorded_calls=[])
        config={'name':'control','kind':'actions','actions':[{'command':'finish'}]}
        record=episode_record(env,config,0)
        interrupted=recover_interrupted(record,make_case())
        self.assertEqual(interrupted['grade']['termination'],'collection_interrupted')
        self.assertFalse(interrupted['grade']['success'])
        with self.assertRaisesRegex(ValueError,'Missing recorded'):
            env.step({'command':'finish'})
        with self.assertRaisesRegex(ValueError,'2.13'):
            Environment(make_case(),framework_version='2.12.0')

    def test_private_abort_is_not_an_agent_operation(self):
        received=[]
        class Fake:
            def call(self,action):
                received.append(action)
                return {'result':{'error':'invalid'},'audit':None,'state_sha256':None}
        env=TakeoverEnvironment(make_case())
        env.runtime=Fake()
        env.step({'command':'__abort__'})
        self.assertEqual(env.history[0]['action'],{'command':'__abort__'})
        self.assertEqual(received,[{'command':'invalid'}])
        self.assertFalse(env.done)

    def test_traffic_starts_before_agent_inference(self):
        sequence=[]
        class FakeRuntime:
            def __init__(self,case): sequence.append('runtime')
            def call(self,action): return {'result':{'handover':True},'audit':audit(),'state_sha256':None}
            def close(self): sequence.append('closed')
        class FakeAgent:
            usage=None
            def act(self,request,timeout):
                sequence.append('inference')
                return {'command':'finish'}
        with patch('pomdp_bench.takeover.Runtime',FakeRuntime), patch('pomdp_bench.evaluation.make_agent',return_value=FakeAgent()):
            result=run_episode(make_case(),{'name':'fake','kind':'actions','actions':[{'command':'finish'}]},'open',0)
        self.assertEqual(sequence,['runtime','inference','closed'])
        self.assertTrue(result['grade']['success'])


if __name__ == '__main__':
    unittest.main()
