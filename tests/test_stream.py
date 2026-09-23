import copy
import unittest
from unittest.mock import patch

from pomdp_bench.collection import validate_definition
from pomdp_bench.evaluation import episode_record, replay
from pomdp_bench.generator import digest
from pomdp_bench.stream import StreamEnvironment, make_case, suite, VERSION
from pomdp_bench.stream_runtime import obligations, booking_errors, matches
from pomdp_bench.worlds import Environment


def records():
    draft={'request_id':'00000000-0000-0000-0000-000000000001','reference':'ORDER-A',
           'revision':1,'kind':'draft','customer':'Alice','address':'One Street',
           'items':[{'sku':'A','quantity':2,'unit_cents':300}]}
    release={'request_id':'00000000-0000-0000-0000-000000000002','reference':'ORDER-A','revision':2,'kind':'release'}
    first={k:copy.deepcopy(draft[k]) for k in ('reference','revision','customer','address','items')}
    first['status']='draft'
    last={**first,'revision':2,'status':'released'}
    return [{'body':draft,'response':{'status':201,'body':{'event_id':draft['request_id'],'order':first}}},
            {'body':release,'response':{'status':201,'body':{'event_id':release['request_id'],'order':last}}}]


class StreamTests(unittest.TestCase):
    def test_receipts_define_obligations_and_retry_does_not_create_work(self):
        data=records()
        orders,releases,errors=obligations(data+[copy.deepcopy(data[0])])
        self.assertEqual(errors,0)
        self.assertEqual(orders['ORDER-A']['status'],'released')
        self.assertEqual(len(releases),1)
        failed=copy.deepcopy(data)
        failed[1]['response']={'status':503}
        self.assertEqual(obligations(failed)[1],{})
        malformed=copy.deepcopy(data)
        malformed[1]['response']['body']=[]
        self.assertEqual(obligations(malformed)[2],1)

    def test_external_duplicates_and_wrong_content_cannot_be_fixed_by_local_rows(self):
        expected=obligations(records())[1]
        booking={**next(iter(expected.values())),'booking_id':'booking-1'}
        self.assertFalse(any(booking_errors(expected,[booking]).values()))
        self.assertEqual(booking_errors(expected,[booking,{**booking,'booking_id':'booking-2'}])['duplicate_bookings'],1)
        self.assertEqual(booking_errors(expected,[])['missing_bookings'],1)
        self.assertEqual(booking_errors(expected,[{**booking,'address':'Wrong'}])['changed_bookings'],1)
        self.assertEqual(booking_errors({},[booking])['unexpected_bookings'],1)
        self.assertFalse(matches({'revision':1},{'revision':True}))

    def test_private_terminal_failure_is_not_feedback_and_replays(self):
        case=make_case()
        action={'command':'finish'}
        call={'request_sha256':digest([VERSION,case,0,action]),'action':action,
              'response':{'result':{'handover':True},'audit':None,'audit_error':'PrivateObserverError','state_sha256':None}}
        env=StreamEnvironment(case,recorded_calls=[call])
        observation=env.step(action)
        self.assertEqual(observation['result'],{'handover':True})
        self.assertNotIn('PrivateObserverError',str(observation))
        config={'name':'artifact','kind':'actions','actions':[action]}
        trace=episode_record(env,config,0)
        self.assertEqual(replay(trace,case)['observer_errors'],1)
        self.assertFalse(trace['grade']['success'])
        self.assertEqual(trace['service_evidence']['runtime'],'postgres-debezium-kafka/1')
        self.assertNotIn('Debezium',str(trace['contract']))
        with self.assertRaisesRegex(ValueError,'2.15'):
            Environment(case,framework_version='2.14.0')

    def test_native_tools_share_the_existing_collection_path(self):
        config={'name':'model','kind':'responses_tools','model':'declared',
                'endpoint_env':'ENDPOINT','api_key_env':'KEY'}
        validate_definition(suite(),[config],['open'],1,10800)


if __name__=='__main__':
    unittest.main()
