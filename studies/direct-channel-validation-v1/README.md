# Direct HTTP channel: frozen integration validation

**Status: plan published before model calls; results pending.** This is a new integration check, independent of the completed [reminder pilot](../verification-reserve-pilot-v1/README.md). It changes the harness and cannot be pooled with that experiment.

## Question, delete, simplify

The previous bridge launched a complete Codex agent runtime to request one JSON action. Its feature denylist missed image generation, its global instructions added context, and its local event timeout became a second deadline. These parts are unnecessary for the benchmark interface.

This check removes that bridge from the execution path. The collector's HTTP adapter calls the existing local model router directly. A single request declares an empty tool list, `tool_choice: none`, fresh complete public input and no stored response chaining. The evaluator contains no tool dispatcher. Both API formats use the same bounded transport, failure accounting and collector. Old bridge sources and failures remain frozen evidence.

## Predeclared design and acceptance

The exact [plan](plan.json) is published with the core implementation and the [local launch snapshot](launch_snapshot.py.txt) before drawing seeds or making model calls.

- One fresh private 128-bit seed, diagnosis and cascade families, standard profile, incident skin, open prompt and one replicate.
- GPT-5.6 Sol and the installed `custom/z-ai/glm-5.3` registration, both requesting `high` reasoning: **four episodes total**.
- 180-second request limit and 900-second episode wall limit. No benchmark retries, outcome-dependent replacements, extra seeds or changed limits during this collection.
- Existing router authentication is loaded only into the process environment; credentials and raw provider bodies are never published. The explicit `x-codex-router-exact-route: 1` header requests the router's exact model route rather than its model failover path.
- Record every terminal outcome, request count and availability of usage, error categories, public request fingerprints, declared tool policy and complete-matrix replay. Accepted collection demonstrates local integration, not provider uptime or task-population performance.

Offline counterexamples must first reject tool-bearing responses even when valid JSON text is also present, truncated responses, multiple candidates, duplicate JSON keys, missing stream completion, undeclared stream events, redirects, oversized bodies and slow-drip deadline extensions. A positive HTTP fixture must complete and replay both families, preserving usage without storing reasoning or credentials.

The live gate is four validated episodes, no unsupported response item/event, and a completed multi-turn action channel for each configured model. If any episode fails, retain it and report the gate as incomplete; no retry makes it disappear. Benchmark task failure and transport/protocol failure are separate observations. No primary model comparison or reminder-effect analysis is planned.

## Boundaries

Empty tools describe what this client sends; response validation and request fingerprints are local evidence, not provider attestation. The router still translates and authenticates requests and can have internal retries or response normalization. The routing header does not disable every internal retry. Native checkpoint identity, upstream hidden capabilities, provider retention and remote cancellation are not independently attested. Reasoning labels do not establish equal compute.

The shared socket deadline closes the active local connection, including slow response headers and body reads. DNS resolution and OS connection establishment are not an externally enforced process deadline. A local disconnect does not prove upstream cancellation or free billing. Missing usage remains unknown.

The frozen plan and sources will not be edited in response to results. The integration gate is distinct from P2's still-open mechanism question and P4's external-validity gate.
