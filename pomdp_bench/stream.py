"""Sparse handover after destructive database recovery and interrupted dispatch."""
from .takeover import TakeoverEnvironment
from .stream_runtime import Runtime, assess

VERSION = 'stream-recovery/1'


def make_case():
    return {'generator_version':VERSION,'family':'stream_recovery','profile':'commerce_handover',
            'domain':'commerce_operations','source_task_id':'constructed/postgres-cdc-rewind-v1',
            'max_steps':200,'seed':2718}


def suite():
    return {'generator_version':VERSION,'cases':[make_case()]}


def validate_case(case):
    if case!=make_case():
        raise ValueError('Unknown stream recovery contract; version scenarios explicitly')


class StreamEnvironment(TakeoverEnvironment):
    generator_version = VERSION
    runtime_version = 'postgres-debezium-kafka/1'
    initial_alert = 'Customers report missing order history and released orders that have not been dispatched. Take over the incident.'

    def validate(self,case):
        validate_case(case)

    def make_runtime(self):
        return Runtime(self.case)

    def outcome(self):
        return assess(self.audit)

    def contract(self):
        return {'family':'incident_takeover',
                'task':'Restore normal order service and fulfil accepted customer instructions without losing records or creating incorrect or duplicate dispatches, then hand over.',
                'workspace':'Root terminal in the isolated operations environment; working directory /srv/commerce. '
                            'All resources inside this environment are in scope. External network access is unavailable.',
                'actions':{'exec':'target: a Bash script. Ordinary stdout, stderr and exit status are returned.',
                           'finish':'no target; hand over the service and end your interaction.'},
                'limits':'200 actions including handover. Each script has 90 seconds and 1 MiB of returned output. '
                         'Services and customer requests continue in real time during your investigation.'}
