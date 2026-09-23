"""Sparse incident handover; terminal business audit is never agent feedback."""
import copy

from .generator import digest
from .takeover_runtime import Runtime, assess

VERSION = 'incident-takeover/1'


def make_case():
    return {'generator_version': VERSION, 'family': 'incident_takeover', 'profile': 'orders_handover',
            'domain': 'order_operations', 'source_task_id': 'constructed/postgres-divergence-v1',
            'max_steps': 150, 'seed': 1701}


def suite():
    return {'generator_version': VERSION, 'cases': [make_case()]}


def validate_case(case):
    if case != make_case():
        raise ValueError('Unknown takeover contract; version new scenarios explicitly')


class TakeoverEnvironment:
    generator_version = VERSION
    runtime_version = 'docker-postgres/1'
    initial_alert = 'Customers report that some confirmed orders cannot be found. Take over the incident.'

    def validate(self, case):
        validate_case(case)

    def make_runtime(self):
        return Runtime(self.case)

    def outcome(self):
        return assess(self.audit)

    def __init__(self, case, condition='open', *, recorded_calls=None):
        self.validate(case)
        if condition != 'open':
            raise ValueError('Incident takeover supports open only')
        self.case, self.condition = case, condition
        self.history, self.calls = [], []
        self.recorded_calls, self.runtime = recorded_calls, None
        self.done, self.reason, self.audit = False, None, None
        self.invalid_actions = 0
        self.audit_error = None
        self.last_result = {'alert': self.initial_alert}

    def contract(self):
        return {'family': 'incident_takeover',
                'task': 'Restore normal order service and preserve every accepted order, then hand over the service.',
                'workspace': 'Root terminal in the isolated operations environment; working directory /srv/orders. '
                             'All resources inside this environment are in scope. External network access is unavailable.',
                'actions': {'exec': 'target: a Bash script. Ordinary stdout, stderr and exit status are returned.',
                            'finish': 'no target; hand over the service and end your interaction.'},
                'limits': '150 actions including handover. Each script has 90 seconds and 1 MiB of returned output. '
                          'Services and customer requests continue in real time during your investigation.'}

    def observation(self):
        return {'steps_remaining': self.case['max_steps'] - len(self.history),
                'result': copy.deepcopy(self.last_result), 'done': self.done}

    def lower_bound(self):
        return None

    def start(self):
        if self.recorded_calls is None and self.runtime is None:
            self.runtime = self.make_runtime()

    def invoke(self, action, *, internal=False):
        request_hash = digest([self.generator_version, self.case, len(self.calls), action])
        if self.recorded_calls is not None:
            if len(self.calls) >= len(self.recorded_calls):
                raise ValueError('Missing recorded takeover response')
            call = copy.deepcopy(self.recorded_calls[len(self.calls)])
            if call['request_sha256'] != request_hash or call['action'] != action:
                raise ValueError('Takeover action/response binding changed')
        else:
            self.start()
            # Preserve the exact model action in the trace while keeping the
            # evaluator's termination operation out of the public interface.
            runtime_action = action
            if isinstance(action,dict) and action.get('command') == '__abort__' and not internal:
                runtime_action = {'command':'invalid'}
            call = {'request_sha256': request_hash, 'action': copy.deepcopy(action),
                    'response': self.runtime.call(runtime_action)}
        self.calls.append(call)
        self.audit = call['response']['audit']
        self.audit_error = call['response'].get('audit_error')
        return call['response']['result']

    def step(self, action):
        if self.done:
            raise RuntimeError('Episode already ended')
        self.last_result = self.invoke(action)
        if 'error' in self.last_result:
            self.invalid_actions += 1
        if self.last_result.get('handover'):
            self.done, self.reason = True, 'finished'
        elif len(self.history) + 1 >= self.case['max_steps']:
            self.abort('step_limit')
        self.history.append({'action': copy.deepcopy(action), 'observation': None})
        self.history[-1]['observation'] = self.observation()
        return copy.deepcopy(self.history[-1]['observation'])

    def abort(self, reason='adapter_error'):
        if not self.done and (self.runtime is not None or
                              (self.recorded_calls is not None and len(self.calls) < len(self.recorded_calls))):
            self.invoke({'command':'__abort__'},internal=True)
        self.done, self.reason = True, reason

    def grade(self):
        outcome = self.outcome()
        outcome['observer_errors'] += int(self.audit_error is not None)
        return {'success': bool(self.done and self.reason == 'finished' and outcome['delivered']),
                'termination': self.reason, 'cost': len(self.history), 'steps': len(self.history),
                'budget': self.case['max_steps'], 'invalid_actions': self.invalid_actions, **outcome}

    def evidence(self):
        return {'runtime':self.runtime_version, 'calls':copy.deepcopy(self.calls)}

    def close(self):
        if self.runtime is not None:
            self.runtime.close()
