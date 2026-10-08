"""Sparse handover after destructive database recovery and interrupted dispatch."""
from .takeover import TakeoverEnvironment
from .stream_runtime import Runtime, assess

VERSION = 'stream-recovery/1'
DELIVERY_VERSION = 'stream-recovery/2'
VERSIONS = (VERSION,DELIVERY_VERSION)


def make_case(version=VERSION):
    if version not in VERSIONS:
        raise ValueError('Unknown stream recovery version')
    case = {'generator_version':VERSION,'family':'stream_recovery','profile':'commerce_handover',
            'domain':'commerce_operations','source_task_id':'constructed/postgres-cdc-rewind-v1',
            'max_steps':200,'seed':2718}
    if version==DELIVERY_VERSION:
        case.update(generator_version=version,profile='customer_delivery',
                    source_task_id='constructed/postgres-cdc-rewind-delivery-v2')
    return case


def suite(version=VERSION):
    return {'generator_version':version,'cases':[make_case(version)]}


def validate_case(case):
    if not isinstance(case,dict) or case!=make_case(case.get('generator_version')):
        raise ValueError('Unknown stream recovery contract; version scenarios explicitly')


class StreamEnvironment(TakeoverEnvironment):
    generator_version = VERSION
    runtime_version = 'postgres-debezium-kafka/1'
    initial_alert = 'Customers report missing order history and released orders that have not been dispatched. Take over the incident.'

    def __init__(self,case,condition='open',*,recorded_calls=None):
        self.generator_version = case['generator_version']
        if self.generator_version==DELIVERY_VERSION:
            self.runtime_version = 'postgres-debezium-kafka/customer-delivery/2'
        super().__init__(case,condition,recorded_calls=recorded_calls)

    def validate(self,case):
        validate_case(case)

    def make_runtime(self):
        return Runtime(self.case,customer_delivery=self.generator_version==DELIVERY_VERSION)

    def outcome(self):
        return assess(self.audit,customer_delivery=self.generator_version==DELIVERY_VERSION)

    def contract(self):
        contract = {'family':'incident_takeover',
                'task':'Restore normal order service and fulfil accepted customer instructions without losing records or creating incorrect or duplicate dispatches, then hand over.',
                'workspace':'Root terminal in the isolated operations environment; working directory /srv/commerce. '
                            'All resources inside this environment are in scope. External network access is unavailable.',
                'actions':{'exec':'target: a Bash script. Ordinary stdout, stderr and exit status are returned.',
                           'finish':'no target; hand over the service and end your interaction.'},
                'limits':'200 actions including handover. Each script has 90 seconds and 1 MiB of returned output. '
                         'Services and customer requests continue in real time during your investigation.'}
        if self.generator_version==DELIVERY_VERSION:
            contract['task'] = ('Restore normal order service and fulfil customer instructions, including pending work, '
                                'without losing records or creating incorrect or duplicate dispatches, then hand over.')
            contract['limits'] = ('200 actions including handover. Each script has 90 seconds and 1 MiB of returned output. '
                                  'Services run in real time and customer work progresses independently of your actions.')
        return contract
