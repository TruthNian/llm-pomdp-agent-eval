"""Offline observation fixtures; these tests are not real model or Docker runs."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pomdp_bench.benchmark import run_benchmark, result_for
from pomdp_bench.collection import validate_definition
from pomdp_bench.stream import DELIVERY_VERSION, make_case, suite
from pomdp_bench.stream_customers import CustomerWorkload, expectations
from pomdp_bench.stream_runtime import assess, commands, customer_plans, initial_batches, obligations
from pomdp_bench.worlds import Environment


def audit_fixture(*,blocked=False,lost_release_ack=False):
    seed = 2718
    history,receipts = {},{}
    def send(bodies):
        result = []
        for body in bodies:
            key = body['request_id']
            if key in receipts:
                response = {'status':200,'body':copy.deepcopy(receipts[key])}
            else:
                chain = history.setdefault(body['reference'],[])
                chain.append(body)
                state = expectations([chain])[0][body['reference']]
                receipts[key] = {'event_id':key,'order':copy.deepcopy(state)}
                response = {'status':201,'body':copy.deepcopy(receipts[key])}
            result.append({'body':copy.deepcopy(body),'response':response})
        return result
    initial = send([body for batch in initial_batches(seed) for body in batch])
    clients = CustomerWorkload(customer_plans(seed),100)
    traffic = []
    for number in range(4):
        bodies = clients.pending()
        if not bodies:
            break
        if blocked:
            rows = [{'body':body,'response':{'status':503}} for body in bodies]
        else:
            rows = send(bodies)
            if lost_release_ack:
                for row in rows:
                    if row['body']['kind']=='release':
                        row['response'] = {'status':None,'error':'timeout'}
        clients.record(rows,112+number*12)
        traffic.append({'elapsed':112+number*12,'commands':rows})
    phases,actual_records = [],list(initial)
    actual_records += [{'body':body,'response':{'status':201,'body':receipts[body['request_id']]}}
                       for chain in customer_plans(seed) for body in chain if body['request_id'] in receipts]
    for phase in range(2):
        inputs = [body for n in range(9000+phase*10,9006+phase*10)
                  for body in commands(n,seed,ending='cancel' if n%3==0 else 'release',amend=n%2==0)]
        new = send(inputs)
        actual_records += new
        orders,releases,_ = obligations(actual_records)
        required = {**orders,**expectations(clients.plans)[0]}
        reads = [{'reference':ref,'response':{'status':200,'body':copy.deepcopy(orders[ref])}
                  if ref in orders else {'status':404,'body':{'error':'not found'}}} for ref in required]
        bookings = [{**copy.deepcopy(value),'booking_id':key,'idempotency_key':key}
                    for key,value in releases.items()]
        phases.append({'commands':new,'reads':reads,'bookings':bookings,
                       'trials':[{'elapsed':200+phase*60,'reads':copy.deepcopy(reads),'bookings':copy.deepcopy(bookings)}]})
    original = initial[0]['body']
    retries = send([original])+[{'body':{**original,'address':original['address']+' altered'},'response':{'status':409}}]
    return {'seed':seed,'initial':initial,'traffic':traffic,'phases':phases,'retry_probes':retries,
            'customer_workload':clients.evidence()}


class DeliveryTests(unittest.TestCase):
    def test_unacknowledged_work_is_not_silently_removed_from_acceptance(self):
        audit = audit_fixture(blocked=True)
        new = assess(audit,customer_delivery=True)
        self.assertFalse(new['delivered'])
        self.assertEqual(new['customers']['unfulfilled_intents'],12)
        self.assertGreater(new['phases'][-1]['required_orders'],new['phases'][-1]['accepted_orders'])
        legacy = copy.deepcopy(audit)
        cohort = {chain[0]['reference'] for chain in customer_plans()}
        for phase in legacy['phases']:
            phase['reads'] = [row for row in phase['reads'] if row['reference'] not in cohort]
        self.assertTrue(assess(legacy)['delivered'])

    def test_lost_response_does_not_mean_lost_order_or_new_intent(self):
        audit = audit_fixture(lost_release_ack=True)
        grade = assess(audit,customer_delivery=True)
        self.assertTrue(grade['delivered'])
        self.assertGreater(grade['traffic_write_failures'],0)
        self.assertEqual(grade['customers']['required_intents'],12)
        self.assertEqual(grade['customers']['fulfilled_intents'],12)
        self.assertLess(grade['customers']['acknowledged_intents'],12)

    def test_retry_identity_is_stable_and_old_incident_history_is_not_replayed(self):
        clients = CustomerWorkload(customer_plans(),0)
        pending = clients.pending()
        clients.record([{'body':body,'response':{'status':503}} for body in pending],12)
        self.assertEqual(clients.pending(),pending)
        initial_ids = {body['request_id'] for batch in initial_batches() for body in batch}
        self.assertFalse(initial_ids & {body['request_id'] for chain in clients.plans for body in chain})
        changed = copy.deepcopy(pending)
        changed[0]['request_id'] = 'replacement-id'
        with self.assertRaisesRegex(ValueError,'identity'):
            clients.record([{'body':body,'response':{'status':503}} for body in changed],24)

    def test_duplicate_external_dispatch_is_an_actual_failure(self):
        audit = audit_fixture()
        wanted = expectations(customer_plans())[1]
        key = next(iter(wanted))
        booking = next(row for row in audit['phases'][-1]['bookings'] if row['client_reference']==key)
        audit['phases'][-1]['bookings'].append({**booking,'booking_id':'extra-booking',
                                              'idempotency_key':'different-dispatch-key'})
        grade = assess(audit,customer_delivery=True)
        self.assertFalse(grade['delivered'])
        self.assertEqual(grade['customers']['unfulfilled_intents'],1)
        self.assertEqual(grade['phases'][-1]['duplicate_bookings'],1)

    def test_demand_and_acknowledgement_evidence_cannot_be_changed(self):
        audit = audit_fixture()
        audit['customer_workload']['acknowledged_elapsed'][0] = 0
        with self.assertRaisesRegex(ValueError,'acknowledgement'):
            assess(audit,customer_delivery=True)
        audit = audit_fixture()
        audit['customer_workload']['plans'].pop()
        with self.assertRaisesRegex(ValueError,'cohort'):
            assess(audit,customer_delivery=True)

    def test_new_semantics_are_versioned_and_accept_normal_native_agents(self):
        with self.assertRaisesRegex(ValueError,'2.17'):
            Environment(make_case(DELIVERY_VERSION),framework_version='2.16.0')
        cfg = {'name':'model','kind':'responses_session','model':'declared','endpoint_env':'ENDPOINT','api_key_env':'KEY'}
        validate_definition(suite(DELIVERY_VERSION),[cfg],['open'],1,10800)

    def test_single_command_reuses_the_collector_and_keeps_grade_private(self):
        audit = audit_fixture()
        class FixtureRuntime:
            def call(self,action):
                return {'result':{'handover':True},'audit':audit,'state_sha256':None}
            def close(self):
                pass
        cfg = {'name':'offline-fixture','kind':'actions','actions':[{'command':'finish'}]}
        with tempfile.TemporaryDirectory() as directory, \
                patch('pomdp_bench.benchmark.configuration',return_value={}), \
                patch('pomdp_bench.stream.Runtime',return_value=FixtureRuntime()):
            output = Path(directory)/'run'
            result = run_benchmark(cfg,output)
            self.assertEqual(result['outcome'],'delivered')
            self.assertEqual(result['attempt_type'],'artifact_control')
            self.assertEqual(result['customers']['fulfilled_intents'],12)
            self.assertIsNone(result['resources']['verified_cost'])
            self.assertTrue((output/'result.md').exists())
            from pomdp_bench.collection import read_run
            _,records = read_run(output)
            self.assertEqual(records[0]['events'][-1]['observation']['result'],{'handover':True})
            with self.assertRaisesRegex(ValueError,'already exists'):
                run_benchmark(cfg,output)

    def test_interruption_and_missing_usage_are_not_capability_failure_or_zero_cost(self):
        trace = {'grade':{'termination':'adapter_error','success':False},'agent':{'name':'model','kind':'responses_session'},
                 'usage':{'requests':1,'requests_with_usage':0,'input_tokens':0,'output_tokens':0},
                 'elapsed_seconds':1,'error':'HTTP 502'}
        result = result_for(trace)
        self.assertEqual(result['outcome'],'execution_interrupted')
        self.assertIsNone(result['resources']['reported_total_tokens'])
        self.assertIsNone(result['resources']['verified_cost'])


if __name__=='__main__':
    unittest.main()
