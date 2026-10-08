"""One incident, one configured agent, one independently verified result."""
import os
from pathlib import Path

from .collection import read_run, run_suite
from .storage import write_json
from .stream import DELIVERY_VERSION, suite
from .stream_runtime import configuration


def result_for(trace):
    grade,usage = trace['grade'],trace.get('usage') or {}
    termination = grade['termination']
    if termination in ('adapter_error','internal_error','collection_interrupted'):
        outcome = 'execution_interrupted'
    elif grade.get('observer_errors'):
        outcome = 'evaluation_error'
    elif termination in ('wall_limit','step_limit'):
        outcome = 'budget_exhausted'
    else:
        outcome = 'delivered' if grade['success'] else 'business_failure'
    input_tokens,output_tokens = usage.get('input_tokens'),usage.get('output_tokens')
    reports,requests = usage.get('requests_with_usage'),usage.get('requests')
    if not reports:
        input_tokens,output_tokens = None,None
    agent = trace['agent']
    return {'benchmark_version':DELIVERY_VERSION, 'outcome':outcome, 'termination':termination,
            'attempt_type':'artifact_control' if agent['kind']=='actions' else 'model',
            'agent':{k:agent[k] for k in ('name','kind','model','options','max_http_retries') if k in agent},
            'business_phases':grade.get('phases',[]), 'customers':grade.get('customers'),
            'resources':{'reported_input_tokens':input_tokens, 'reported_output_tokens':output_tokens,
                         'reported_total_tokens':None if input_tokens is None or output_tokens is None else input_tokens+output_tokens,
                         'usage_reports':reports, 'requests':requests,
                         'usage_completeness':'unknown' if reports is None else 'complete' if reports==requests else 'partial',
                         'reported_cached_input_tokens':usage.get('cached_input_tokens'),
                         'total_elapsed_seconds':trace['elapsed_seconds'],
                         'verified_cost':None, 'cost_status':'not_verified'},
            'diagnostics':{'traffic_write_failures':grade.get('traffic_write_failures'),
                           'error':trace.get('error')},
            'scope':'Observed delivery on one constructed incident and declared agent configuration; not a population capability estimate.'}


def save_result(output):
    _,records = read_run(output)
    if len(records)!=1:
        raise ValueError('A benchmark result requires exactly one complete attempt')
    result = result_for(records[0])
    write_json(output/'result.json',result,replace=False)
    customers = result['customers'] or {}
    resources = result['resources']
    def reported(key):
        value = resources[key]
        return 'unknown' if value is None else value
    lines = ['# Incident benchmark result','',f"Attempt type: {result['attempt_type']}",'',f"Outcome: **{result['outcome']}**",'',
             f"Customer intents fulfilled: {customers.get('fulfilled_intents','unknown')} / {customers.get('required_intents','unknown')}",
             f"Reported input tokens: {reported('reported_input_tokens')}",
             f"Reported output tokens: {reported('reported_output_tokens')}",
             f"Reported total tokens: {reported('reported_total_tokens')}",
             f"Usage coverage: {resources['usage_reports']} / {resources['requests']} recorded requests ({resources['usage_completeness']})",
             f"Total elapsed seconds (including setup and independent audit): {resources['total_elapsed_seconds']}",
             'Verified expense: unknown; no zero cost or API list-price assumption.','',
             'Order state and external dispatches are checked independently before and after restart.',
             'HTTP write failures remain diagnostic events. Actions remain an internal budget.',
             'See result.json for business errors, usage coverage and acknowledgement waits; private/ contains the complete audit.',
             '',result['scope'],'']
    (output/'result.md').write_text('\n'.join(lines),encoding='utf-8')
    return result


def run_benchmark(agent,output,*,runtime_config=None,wall_seconds=10800):
    if isinstance(agent,list) and len(agent)==1:
        agent = agent[0]
    if not isinstance(agent,dict):
        raise ValueError('Provide one agent configuration object or a one-element array')
    previous = os.environ.get('POMDP_STREAM_CONFIG')
    try:
        if runtime_config is not None:
            os.environ['POMDP_STREAM_CONFIG'] = str(Path(runtime_config).resolve())
        configuration()  # Check the pinned runtime configuration before creating an attempt.
        run_suite(suite(DELIVERY_VERSION),[agent],['open'],1,output,wall_seconds)
        return save_result(output)
    finally:
        if previous is None:
            os.environ.pop('POMDP_STREAM_CONFIG',None)
        else:
            os.environ['POMDP_STREAM_CONFIG'] = previous
