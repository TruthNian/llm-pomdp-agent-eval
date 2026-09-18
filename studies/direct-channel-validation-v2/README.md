# Corrected direct channel: independent integration validation

**Status: implementation, plan and launcher published before drawing evaluation seeds; results pending.**

## Question and simplify

The [2.3 validation](../direct-channel-validation-v1/README.md) retained four first-request failures. Development diagnostics now identify three unnecessary assumptions in that implementation:

1. A reasoning content part is not an external tool. The documented Responses stream allows `reasoning_text`; it must belong to a declared reasoning item and is ignored as action content.
2. The response need not repeat the requested wire format in a header. With no media header, an explicitly streaming request still uses the SSE parser.
3. Completed item events already contain the answer. A final completed response with an empty output array need not repeat it. Item identities, closure, one assistant action and whole-response completion remain required; conflicting nonempty terminal actions are rejected.

GPT authentication also does not require global session sharing. The installed router accepts this client's existing authorized Codex login on its own requests. The [local launcher](launch_snapshot.py.txt) loads it only into process memory/environment, supplies the account selector and never writes login, router configuration or shared-consent state. GLM uses the router caller key. The generic benchmark does not discover credentials.

These changes follow observed protocol shapes. They do not remove tool-call rejection, duplicate-key rejection, deadline/size limits, complete-matrix accounting or the public-observation boundary.

## Frozen plan

The exact [plan](plan.json), launcher and core source are published before this collection. One new private 128-bit seed generates diagnosis and cascade cases. Both configured models request `high` reasoning, the open condition and one replicate: **four episodes**, each attempted once.

The request deadline is **240 seconds** and episode wall limit **1,800 seconds**, fixed for both models before evaluation. A development GLM reasoning stream took roughly 156 seconds, motivating headroom for this transport check. These limits differ from the previous pilot and prohibit pooling its results. No timeout, source, configuration or sample is changed in response to this run.

Acceptance requires all four trajectories to replay, a completed multi-turn action channel for both models and no adapter/collection failure. Task success is reported separately. Every terminal failure stays in the matrix. Record reported usage and its availability; missing usage is unknown, not zero.

Development probes use the public seed-zero first observation and are separate from the evaluation matrix. They are debugging evidence, not model scores, held-out trials or replacements for previous failed episodes. Their observed event types are saved without provider text, reasoning, credentials or account identifiers.

The [development diagnostic record](development-diagnostics.json) includes all eight requests: six parser failures while isolating the boundary and two completed actions after the relevant fixes. The [final diagnostic script snapshot](diagnostic_snapshot.py.txt) records structural fields only; earlier script revisions are identified by hash. These evolving-code probes are not a fixed statistical experiment.

## Boundaries

The native headerless stream and empty terminal output are observed gateway behaviors, not a claim that every Responses server behaves identically. Reasoning content parts are documented in the [official streaming event reference](https://developers.openai.com/api/reference/resources/responses/streaming-events#response.content_part.added).

The exact-route request does not attest checkpoint identity, equal reasoning compute, gateway-internal retries or remote cancellation. Request hashes prove local consistency, not upstream behavior. One seed and two synthetic task families cannot establish population capability, parameter-scale effects, post-training causes, a reminder mechanism or real-work validity.

The original 2.3 plan, sources and failed outcomes remain frozen. Any outcome from this validation is a new integration result.
