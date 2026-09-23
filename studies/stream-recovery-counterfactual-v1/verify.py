"""Verify the two retained data-completeness artifact experiments."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pomdp_bench.stream_runtime import assess

ROOT=Path(__file__).resolve().parent


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))


def main():
    plan,execution=read('plan.json'),read('execution.json')
    for name,expected in execution['file_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('Published bytes changed: '+name)
    original=read(plan['source_study'])
    if hashlib.sha256((ROOT/plan['source_study']).read_bytes()).hexdigest()!=plan['source_evidence_sha256']:
        raise ValueError('Source attempt changed')
    original_events=original['records'][0]['events'][:-1]
    counts=[]
    for arm in plan['arms']:
        data=read(arm+'.json')
        if (data['status']!='completed' or data['arm']!=arm or data['exit_code_mismatches']
                or data['git_revision']!=execution['source_commit']
                or data['source_sha256']!=original['source_sha256']
                or data['plan_sha256']!=hashlib.sha256((ROOT/'plan.json').read_bytes()).hexdigest()):
            raise ValueError('Counterfactual execution differs from its declared basis')
        expected=[e['action'] for e in original_events]
        if arm=='restore_missing':
            expected += [{'command':'exec','target':(ROOT.parent/'stream-recovery-v1/controls/restore.sh').read_text()},
                         {'command':'exec','target':(ROOT/'restore-missing.sh').read_text()}]
        expected.append({'command':'finish'})
        if [e['action'] for e in data['events']]!=expected:
            raise ValueError('Undeclared action or omitted original command')
        audit=data['events'][-1]['response']['audit']
        if (audit['image']!=plan['runtime']['image'] or audit['components']!=plan['runtime']['components']
                or [[x['body'] for x in batch['commands']] for batch in audit['traffic']]!=plan['preloaded_customer_batches']):
            raise ValueError('Runtime or matched customer workload changed')
        grade=assess(audit)
        if grade!=data['grade'] or grade['observer_errors'] or grade['retry_errors']:
            raise ValueError('Business regrading differs or observer failed')
        if grade['delivered']!=(arm=='restore_missing'):
            raise ValueError('Published causal contrast did not reproduce')
        for phase in grade['phases']:
            if (phase['order_errors'],phase['missing_bookings'])!=((0,0) if arm=='restore_missing' else (12,9)):
                raise ValueError('Published missing-history outcome changed')
        counts.append([(p['accepted_orders'],p['accepted_releases']) for p in grade['phases']])
    if counts[0]!=counts[1]:raise ValueError('Business workload was not matched')
    print('Verified matched original/rescue artifacts: 12 missing orders and 9 dispatches resolve through data-only recovery.')


if __name__=='__main__':main()
