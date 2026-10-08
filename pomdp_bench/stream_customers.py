"""A finite customer cohort: retry identical commands and verify actual outcomes."""
import copy
import json

CUSTOMERS = 12
RETRY_SECONDS = 12
HANDOVER_SECONDS = 60
POLICY = (
    '\n## Customer recovery\n\n'
    'Customers with pending work retry the same request ID and body every 12 seconds. '
    'A retry does not create a new order or authorize another dispatch. '
    'During incident recovery, maintenance may postpone customer work. After handover, '
    'customers continue retrying pending commands for 60 seconds. Fulfil their requested '
    'work and preserve the resulting orders and dispatches through service restart. '
    'Draft and cancelled orders must not be dispatched.\n'
)


def matches(expected,actual):
    if not isinstance(actual,dict):
        return False
    try:
        return (json.dumps({k:actual.get(k) for k in expected},sort_keys=True,allow_nan=False)==
                json.dumps(expected,sort_keys=True,allow_nan=False))
    except (ValueError,TypeError):
        return False


def expectations(plans):
    """Project customers' requested work, independently of HTTP success receipts."""
    orders, releases = {}, {}
    for chain in plans:
        state = None
        for body in chain:
            if body['kind'] == 'draft':
                state = {k:copy.deepcopy(body[k]) for k in ('reference','revision','customer','address','items')}
                state['status'] = 'draft'
            else:
                if state is None or state['reference'] != body['reference'] or state['status'] != 'draft':
                    raise ValueError('Invalid customer command sequence')
                state['revision'] = body['revision']
                if body['kind'] == 'amend':
                    state.update({k:copy.deepcopy(body[k]) for k in ('customer','address','items')})
                elif body['kind'] in ('release','cancel'):
                    state['status'] = 'released' if body['kind']=='release' else 'cancelled'
                else:
                    raise ValueError('Unknown customer command')
            if body['kind'] == 'release':
                releases[body['request_id']] = {
                    'client_reference':body['request_id'], 'order_reference':body['reference'],
                    **{k:copy.deepcopy(state[k]) for k in ('customer','address','items')}}
        if state is None or state['reference'] in orders:
            raise ValueError('Empty or duplicate customer intent')
        orders[state['reference']] = state
    return orders,releases


class CustomerWorkload:
    def __init__(self, plans, arrived_elapsed):
        expectations(plans)
        self.plans = copy.deepcopy(plans)
        self.arrived_elapsed = arrived_elapsed
        self.positions = [0]*len(plans)
        self.acknowledged_elapsed = [None]*len(plans)

    def pending(self):
        return [copy.deepcopy(chain[position]) for chain,position in zip(self.plans,self.positions)
                if position<len(chain)]

    def record(self, records, elapsed):
        if [item['body'] for item in records] != self.pending():
            raise ValueError('Customer retries changed their request identity or sequence')
        active = [i for i,(chain,position) in enumerate(zip(self.plans,self.positions)) if position<len(chain)]
        for index,item in zip(active,records):
            response,body = item['response'],item['body']
            position = self.positions[index]
            expected = expectations([self.plans[index][:position+1]])[0][body['reference']]
            value = response.get('body')
            actual = value.get('order') if isinstance(value,dict) else None
            if not isinstance(actual,dict):
                continue
            if (response.get('status') in (200,201) and value.get('event_id')==body['request_id']
                    and matches(expected,actual)):
                self.positions[index] += 1
                if self.positions[index] == len(self.plans[index]):
                    self.acknowledged_elapsed[index] = elapsed

    def evidence(self):
        return {'plans':copy.deepcopy(self.plans), 'arrived_elapsed':self.arrived_elapsed,
                'acknowledged_elapsed':list(self.acknowledged_elapsed)}


def completion(orders, releases, reads, bookings):
    """Count fulfilled customer intents without adding overlapping error categories."""
    observations = {item['reference']:item['response'] for item in reads}
    completed = 0
    for reference,expected in orders.items():
        response = observations.get(reference,{})
        actual = response.get('body')
        correct = response.get('status')==200 and matches(expected,actual)
        wanted = [v for v in releases.values() if v['order_reference']==reference]
        observed = [v for v in bookings if v.get('order_reference')==reference]
        if wanted:
            correct = correct and len(wanted)==len(observed)==1 and matches(wanted[0],observed[0])
        else:
            correct = correct and not observed
        completed += int(correct)
    return {'required_intents':len(orders), 'fulfilled_intents':completed,
            'unfulfilled_intents':len(orders)-completed}
