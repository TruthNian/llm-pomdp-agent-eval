# Continuous native recovery screen

Planned fresh model attempt; no incident outcome has been measured with this adapter yet.
The [plan](plan.json) keeps the same scenario, immutable image, 200-action budget,
600-second request timeout, 10800-second episode limit and 16 MB wire limit as
the completed [stateless attempt](../stream-recovery-v1/README.md).

The newly versioned adapter retains the native assistant/function dialogue and
encrypted reasoning state. It removes an identified measurement limitation without
adding incident information, guidance, tools or evaluator feedback. The environment
source hashes and image match the earlier four qualification controls. No control
result or recovery script enters the model's observation.

Two development protocol diagnostics are retained separately. Each made two requests
without executing an environment or scoring a task. The first completed exec/finish
but emitted zero reasoning items, leaving the reasoning-continuity assertion unexercised
and recorded as a failed diagnostic assertion. The second used a small combinatorial
prompt to exercise reasoning; native continuation succeeded with encrypted state.
Mathematical correctness was not scored. Both original records remain unchanged.

Public auditing reconstructs the request projection from recorded assistant/function
items and tool observations, with opaque reasoning represented only by hashes. It
does not claim to reproduce encrypted request bytes. See the [adapter contract](../../docs/MODEL_ADAPTERS.md).

A clean delivery rejects this candidate as continuous-agent high-difficulty evidence.
A business failure needs causal attribution; a protocol, runtime, capacity or observer
failure does not demonstrate cognitive difficulty. A single unpaired comparison of
real-time attempts does not isolate the causal effect of conversation continuity.
