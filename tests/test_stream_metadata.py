"""New progress events must not authorize actions or conceal invalid results."""
import json
import unittest

from pomdp_bench.model_io import AdapterError, HttpAgent, ResponseStream, action_text
from tests.test_model_io import config, endpoint, response, send, sse
from tests.test_native_session import output, stream


class StreamMetadataTests(unittest.TestCase):
    def test_native_metadata_is_audited_without_becoming_an_action_or_public_body(self):
        raw = (sse({'type':'response.metrics.updated','metadata':'PRIVATE-METADATA-CANARY',
                    'delta':'{"command":"exec","target":"unrequested command"}'})+
               stream(output(finish=True)))
        for retries in (0,2):
            with self.subTest(retries=retries),endpoint(lambda h,_:send(h,raw,'text/event-stream')):
                agent = HttpAgent({**config('responses_session'),'max_http_retries':retries})
                self.assertEqual(agent.act({'protocol_version':1,'task':{},'observation':{},'history':[]},5),
                                 {'command':'finish'})
            audit = agent.request_audit[0]
            wire = audit['wire_attempts'][0] if retries else audit
            self.assertEqual(wire['ignored_stream_event_types'],{'response.metrics.updated':1})
            self.assertNotIn('PRIVATE-METADATA-CANARY',json.dumps(audit))
            self.assertNotIn('unrequested command',json.dumps(audit))
            self.assertEqual(agent.usage['requests'],1)
            self.assertEqual(agent.session.turns,1)

    def test_metadata_never_substitutes_for_completion_or_closes_an_unfinished_call(self):
        for raw in (sse({'type':'future.provider.event','status':'completed'}),
                    sse({'type':'response.output_item.added','output_index':0,'item':{
                        'type':'function_call','id':'pending','name':'finish','call_id':'pending','arguments':'{}'}})+
                    sse({'type':'future.provider.event','status':'completed'})+
                    sse({'type':'response.completed','response':{'status':'completed','output':[]}})):
            with self.subTest(raw=raw),self.assertRaises(AdapterError):
                parser = ResponseStream(('exec','finish'))
                parser.feed(raw,final=True)

    def test_undeclared_action_events_are_rejected_even_without_an_output_item(self):
        events = [{'type':kind} for kind in ('response.web_search_call.searching',
                  'response.new_tool.started','response.future_call_input.delta',
                  'response.function_call_arguments.future','response.output_item.future')]
        events += [
            {'type':'future.provider.event','arguments':'{}'},
            {'type':'future.provider.event','item':{'type':'message'}},
            {'type':'future.provider.event','response':{'output':[{'type':'function_call','name':'finish'}]}},
        ]
        for event in events:
            with self.subTest(event=event),self.assertRaises(AdapterError) as raised:
                ResponseStream(('exec','finish')).feed(sse(event))
            self.assertEqual(raised.exception.code,'unexpected_tool')

    def test_metadata_cannot_hide_explicit_failure_and_does_not_trigger_retries(self):
        for event in ({'type':'future.provider.event','error':{'message':'PRIVATE-ERROR-CANARY'}},
                      {'type':'future.provider.event','status':'incomplete'},
                      {'type':'future.provider.event','response':{'status':'failed'}},
                      {'type':'provider.cancelled'}):
            with self.subTest(event=event),endpoint(lambda h,_:send(h,sse(event),'text/event-stream')) as received:
                agent = HttpAgent({**config(),'max_http_retries':2})
                with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},5)
            self.assertEqual(len(received),1)
            wire = agent.request_audit[0]['wire_attempts'][0]
            self.assertEqual(wire['last_stream_event_type'],event['type'])
            self.assertNotIn('PRIVATE-ERROR-CANARY',json.dumps(agent.request_audit))
            self.assertNotIn('retryable_transport',wire)

    def test_metadata_after_completion_is_rejected(self):
        parser = ResponseStream()
        parser.feed(sse({'type':'response.completed','response':response()}))
        with self.assertRaises(AdapterError) as raised:
            parser.feed(sse({'type':'future.provider.event'}))
        self.assertEqual(raised.exception.code,'protocol_error')

    def test_refusal_is_message_content_and_never_a_valid_action(self):
        item = {'type':'message','id':'refusal','role':'assistant','status':'completed',
                'content':[{'type':'refusal','refusal':'Cannot act.'}]}
        events = [
            {'type':'response.output_item.added','output_index':0,'item':{**item,'status':'in_progress'}},
            {'type':'response.content_part.added','output_index':0,'item_id':'refusal','part':item['content'][0]},
            {'type':'response.refusal.delta','output_index':0,'item_id':'refusal','delta':'Cannot act.'},
            {'type':'response.refusal.done','output_index':0,'item_id':'refusal','refusal':'Cannot act.'},
            {'type':'response.content_part.done','output_index':0,'item_id':'refusal','part':item['content'][0]},
            {'type':'response.output_item.done','output_index':0,'item':item},
            {'type':'response.completed','response':{'status':'completed','output':[item]}},
        ]
        parser = ResponseStream(('exec','finish'))
        parser.feed(b''.join(sse(event) for event in events),final=True)
        for kind in ('responses','responses_tools','responses_session'):
            with self.subTest(kind=kind),self.assertRaises(AdapterError):action_text(parser.result,kind)

    def test_invalid_event_names_do_not_publish_their_contents(self):
        event = {'type':'PRIVATE-EVENT-CANARY '*10}
        with endpoint(lambda h,_:send(h,sse(event),'text/event-stream')):
            agent = HttpAgent(config())
            with self.assertRaises(AdapterError):agent.act({'task':{},'history':[]},5)
        self.assertEqual(agent.request_audit[0]['last_stream_event_type'],'<invalid>')
        self.assertNotIn('PRIVATE-EVENT-CANARY',json.dumps(agent.request_audit))


if __name__=='__main__':unittest.main()
