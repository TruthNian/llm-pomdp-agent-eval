# Corrected direct channel: independent integration validation

**Status: four attempts retained and replayed; two successful deliveries, two channel failures. The predeclared all-four integration gate did not pass.**

## Result and decision

The [frozen collection commit](https://github.com/TruthNian/llm-pomdp-agent-eval/commit/d0c540567107b555aabf04abe3fb32d1e84db924), plan and launcher were public before preparation. The [push workflow](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35343688568) was created at 12:15:15 UTC; preparation began at 12:15:34 UTC on 2026-09-18. All 14 source hashes, the plan and launcher match that commit. The [sanitized evidence](evidence.json) records every attempt and all 19 reconstructed public request fingerprints.

| Configured model | Family | Accepted | Actions | Termination | Elapsed seconds |
|---|---|---:|---:|---|---:|
| GPT-5.6 Sol | diagnosis | No | 1 | Stream failure/incomplete event on request 2 | 11.72 |
| custom/z-ai/glm-5.3 | diagnosis | No | 1 | Request 2 reached the fixed 240-second deadline | 387.27 |
| custom/z-ai/glm-5.3 | cascade | Yes | 9 | Verified and finished | 195.60 |
| GPT-5.6 Sol | cascade | Yes | 6 | Verified and finished | 34.69 |

Each configured model completed a genuine multi-turn task. This is positive integration evidence, **not passage of the stricter predeclared four-episode gate**. The two failures remain in the matrix; no retry, replacement, timeout increase or additional evaluation seed was used. Their precise upstream cause is not identified: the stored stream failure category does not include raw provider error messages.

There were 19 benchmark requests and 17 complete usage reports. Token totals for each interrupted trajectory remain unknown. The successful GLM trajectory reported 27,261 input and 11,396 output tokens; the successful GPT trajectory reported 11,545 input and 825 output tokens. These are descriptions of two runs, not estimates of model efficiency; models, tokenizers and gateway accounting differ.

The launcher's before/after byte comparison confirmed no change to the login, router configuration or global session-consent files during collection. Authentication values, account identifiers, private seeds, raw provider bodies and reasoning text are not published.

**Decision:** retain the protocol corrections and complete trajectories; do not scale this endpoint into a model-comparison study. Use a bounded public-history diagnostic to isolate remaining failure events and latency separately from held-out scoring. Offline P3 work on discovery/recovery can proceed under its own constructive-witness and negative-control gates; it does not depend on claiming perfect endpoint reliability.

**Release boundary:** the frozen collection commit passed 104 tests (34 channel tests) and four Windows/Linux CI jobs. A subsequent offline regression check found that parsing an invalid action during stream-consistency checking could discard available usage. The final release compares completed message content before action parsing and adds that regression test: 105 tests (35 channel tests). The published trajectories remain attached to the earlier exact source commit; this later accounting fix was not applied to or rerun on those attempts. Final offline demo/replay and historical checks are reported separately.

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
