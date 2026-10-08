"""Transient server errors must not corrupt dialogue or repeat executed actions."""
import copy
from datetime import datetime, timezone
from email.utils import format_datetime
import json
import unittest
from unittest.mock import patch

from pomdp_bench.agents import validate_agent_version, validate_config
from pomdp_bench.model_io import AdapterError, HttpAgent, retry_after_seconds
from tests.test_model_io import config, endpoint, response, send, sse
from tests.test_native_session import output


class HttpRetryTests(unittest.TestCase):
    def test_truncated_native_stream_retries_without_executing_a_partial_call(self):
        bodies = []
        result = {'model':'test-model','status':'completed','output':output(),
                  'usage':{'input_tokens':12,'output_tokens':7}}
        result['output'][-1].update(name='finish',arguments='{}')
        def reply(handler,body):
            bodies.append(copy.deepcopy(body))
            if len(bodies)==1:
                partial = {'type':'response.output_item.added','output_index':0,
                           'item':{'type':'function_call','id':'partial','name':'exec','call_id':'partial_call','arguments':''}}
                send(handler,sse(partial),'text/event-stream')
            else:
                send(handler,json.dumps(result).encode())
        with endpoint(reply),patch('pomdp_bench.model_io.time.sleep'):
            agent = HttpAgent({**config('responses_session'),'max_http_retries':2})
            request = {'protocol_version':1,'task':{},'observation':{},'history':[]}
            self.assertEqual(agent.act(request,timeout=5),{'command':'finish'})
        self.assertEqual(bodies[0],bodies[1])
        self.assertEqual(len(agent.request_audit),1)
        self.assertEqual(agent.usage['requests'],2)
        self.assertEqual(agent.usage['requests_with_usage'],1)
        self.assertTrue(agent.request_audit[0]['wire_attempts'][0]['retryable_transport'])
        self.assertNotIn('partial_call',json.dumps(agent.request_audit[0].get('response_items')))

    def test_explicit_model_incomplete_event_is_not_a_transport_retry(self):
        bodies = []
        def reply(handler,body):
            bodies.append(body)
            send(handler,sse({'type':'response.incomplete','response':{'status':'incomplete'}}),'text/event-stream')
        with endpoint(reply):
            agent = HttpAgent({**config(),'max_http_retries':2})
            with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},timeout=5)
        self.assertEqual(len(bodies),1)
        self.assertNotIn('retryable_transport',agent.request_audit[0]['wire_attempts'][0])

    def test_classified_connection_and_request_timeout_can_be_retried(self):
        for code in ('transport_error','timeout'):
            with self.subTest(code=code), \
                    patch.dict('os.environ',{'WIRE_ENDPOINT':'http://127.0.0.1:1/responses','WIRE_KEY':'fixture'}), \
                    patch('pomdp_bench.model_io.time.sleep'), \
                    patch('pomdp_bench.model_io.exchange',side_effect=[
                        AdapterError('Network interruption',code,retryable_transport=True),response()]) as wire:
                agent = HttpAgent({**config(),'max_http_retries':2})
                self.assertEqual(agent.act({'task':{},'history':[]},timeout=5),{'command':'finish'})
                self.assertEqual(wire.call_count,2)
                self.assertEqual(wire.call_args_list[0].args[2],wire.call_args_list[1].args[2])

    def test_real_http_502_resends_identical_body_without_fabricating_usage(self):
        bodies = []
        def reply(handler,body):
            bodies.append(copy.deepcopy(body))
            if len(bodies)==1:
                send(handler,b'PRIVATE-UPSTREAM-ERROR',status=502)
            else:
                send(handler,json.dumps(response()).encode())
        with endpoint(reply),patch('pomdp_bench.model_io.time.sleep'):
            agent = HttpAgent({**config(),'max_http_retries':2})
            self.assertEqual(agent.act({'task':{},'history':[]},timeout=5),{'command':'finish'})
        self.assertEqual(bodies[0],bodies[1])
        self.assertEqual(agent.usage['requests'],2)
        self.assertEqual(agent.usage['requests_with_usage'],1)
        self.assertEqual(agent.usage['input_tokens'],12)
        audit = agent.request_audit[0]
        self.assertEqual([w['outcome'] for w in audit['wire_attempts']],['http_error','response_received'])
        self.assertEqual(audit['wire_attempts'][0]['http_status'],502)
        self.assertNotIn('PRIVATE-UPSTREAM-ERROR',json.dumps(audit))

    def test_native_continuation_is_appended_once_across_a_retry(self):
        config_native = {**config('responses_session'),'max_http_retries':2}
        bodies = []
        first = {'model':'test-model','status':'completed','output':output(),
                 'usage':{'input_tokens':12,'output_tokens':7}}
        second = copy.deepcopy(first)
        second['output'][0]['id'] = 'rs_2'
        second['output'][-1].update(id='fn_2',call_id='call_2',name='finish',arguments='{}')
        def exchange(*args,**kwargs):
            bodies.append(json.loads(args[2]))
            if len(bodies)==2:
                raise AdapterError('Endpoint HTTP status 502','http_error',http_status=502)
            return first if len(bodies)==1 else second
        with patch.dict('os.environ',{'WIRE_ENDPOINT':'http://127.0.0.1:1/responses','WIRE_KEY':'fixture'}), \
                patch('pomdp_bench.model_io.exchange',side_effect=exchange),patch('pomdp_bench.model_io.time.sleep'):
            agent = HttpAgent(config_native)
            initial = {'protocol_version':1,'task':{},'observation':{},'history':[]}
            action = agent.act(initial,timeout=20)
            observation = {'result':'actual output'}
            next_request = {**initial,'observation':observation,'history':[{'action':action,'observation':observation}]}
            self.assertEqual(agent.act(next_request,timeout=20),{'command':'finish'})
        self.assertEqual(bodies[1],bodies[2])
        self.assertEqual(sum(i.get('type')=='function_call_output' for i in bodies[2]['input']),1)
        self.assertEqual(len(agent.request_audit),2)
        self.assertEqual(agent.usage['requests'],3)
        self.assertEqual(agent.usage['requests_with_usage'],2)
        self.assertNotIn('encrypted_content"',json.dumps(agent.request_audit))

    def test_retries_are_bounded_and_legacy_default_does_not_retry(self):
        for retries,expected in ((None,1),(0,1),(2,3)):
            cfg = config()
            if retries is not None:cfg['max_http_retries'] = retries
            error = AdapterError('Endpoint HTTP status 502','http_error',http_status=502)
            with patch.dict('os.environ',{'WIRE_ENDPOINT':'http://127.0.0.1:1/responses','WIRE_KEY':'fixture'}), \
                    patch('pomdp_bench.model_io.exchange',side_effect=error) as wire, \
                    patch('pomdp_bench.model_io.time.sleep'):
                agent = HttpAgent(cfg)
                with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},timeout=20)
            self.assertEqual(wire.call_count,expected)
            self.assertEqual(agent.usage['requests'],expected)
            self.assertEqual(agent.usage['requests_with_usage'],0)

    def test_client_protocol_timeout_and_oversize_errors_are_not_retried(self):
        for error in (AdapterError('Unauthorized','http_error',http_status=401),
                      AdapterError('Quota','http_error',http_status=429),
                      AdapterError('Incomplete call','incomplete_response'),
                      AdapterError('Ambiguous call','protocol_error'),
                      AdapterError('Deadline','timeout'),
                      AdapterError('Too large','response_too_large')):
            with self.subTest(code=error.code), \
                    patch.dict('os.environ',{'WIRE_ENDPOINT':'http://127.0.0.1:1/responses','WIRE_KEY':'fixture'}), \
                    patch('pomdp_bench.model_io.exchange',side_effect=error) as wire:
                agent = HttpAgent({**config(),'max_http_retries':2})
                with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},timeout=20)
                self.assertEqual(wire.call_count,1)

    def test_retry_after_cannot_exceed_the_wall_deadline_or_delay_cap(self):
        for delay in (10,120):
            with patch.dict('os.environ',{'WIRE_ENDPOINT':'http://127.0.0.1:1/responses','WIRE_KEY':'fixture'}), \
                    patch('pomdp_bench.model_io.exchange',side_effect=AdapterError(
                        'Endpoint HTTP status 503','http_error',http_status=503,retry_after=delay)) as wire:
                agent = HttpAgent({**config(),'max_http_retries':2})
                with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},timeout=5)
                self.assertEqual(wire.call_count,1)
        self.assertEqual(retry_after_seconds('2'),2)
        self.assertIsNone(retry_after_seconds('inf'))
        self.assertIsNone(retry_after_seconds('untrusted text'))
        self.assertEqual(retry_after_seconds(format_datetime(datetime(2020,1,1,tzinfo=timezone.utc))),0)

    def test_retry_configuration_is_explicit_bounded_and_versioned(self):
        for value in (True,-1,3,1.0):
            with self.assertRaises(ValueError):validate_config({**config(),'max_http_retries':value})
        cfg = {**config(),'max_http_retries':2}
        validate_config(cfg)
        with self.assertRaisesRegex(ValueError,'2.17.1'):validate_agent_version(cfg,'2.17.0')
        validate_agent_version(cfg,'2.17.1')


if __name__=='__main__':
    unittest.main()
