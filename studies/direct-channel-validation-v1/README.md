# Direct HTTP channel: frozen integration validation

**Status: all four planned attempts retained and replayed; live integration gate failed.** This is a new integration check, independent of the completed [reminder pilot](../verification-reserve-pilot-v1/README.md). It changes the harness and cannot be pooled with that experiment.

## Recorded result and decision

The [implementation, plan and launcher](https://github.com/TruthNian/llm-pomdp-agent-eval/commit/7dd8727630c2b64836e6974e18bb34ed50fb451a) were public before preparation and collection. The [push workflow](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35338670776) was created at 11:14:46 UTC; preparation began at 11:15:00 UTC on 2026-09-18. All 14 core file hashes, the plan and launcher match that commit. See the [sanitized evidence](evidence.json) for ordered attempts, request hashes and error categories.

| Configured model | Planned episodes | Accepted tasks | Observed termination |
|---|---:|---:|---|
| GPT-5.6 Sol | 2 | 0 | HTTP 401 on each first request |
| custom/z-ai/glm-5.3 | 2 | 0 | Non-output-text stream content part rejected on each first request |

All four attempts ended before an environment action. There were exactly four benchmark requests and no benchmark retry or replacement. None returned complete usage; their token totals are **unknown**, not zero. All four trajectories replay and their public request fingerprints can be reconstructed from the private cases. Replay verifies faithful failure accounting; it does not turn a failed integration into a successful one.

Post-failure read-only inspection of the installed router module found a usable, unexpired native login with session sharing disabled in the local shell. Its source requires sharing to substitute native authentication for the router caller key. That identifies a missing prerequisite consistent with the HTTP 401 responses; it is not an attestation of the running service's environment or the exact origin of each status. Seeing a model in the local catalogue is insufficient evidence of permission to invoke it through this endpoint.

One separate [diagnostic script](diagnostic_snapshot.py.txt) then made **one constant-output GLM request**, without a benchmark case or score. It returned a completed action, 94 reported input tokens, 6 output tokens and 0 reported reasoning tokens. The original non-text part subtype was not stored, and this simpler request did not reproduce that failure. Its reported model string differed from the configured alias; that observation alone neither proves a substituted model nor attests its identity. The diagnostic is not a fifth benchmark episode or a replacement for either failed GLM trajectory.

**Decision:** ship the tested protocol implementation with this explicit integration limit; do not expand the model study or loosen parsing to make these results disappear. The next live gate requires permission through the intended route and a reviewed protocol-shape diagnosis for the full public-history input. Any compatibility change needs counterexamples proving that tool-bearing content is still rejected, followed by a separately frozen validation. An easy one-action smoke test cannot substitute for multi-turn integration.

Offline acceptance passed: **93 tests**, including **23 channel tests**, four Windows/Linux CI jobs on Python 3.11/3.13, 24 offline demo trajectories, historical replay and 156 immutable archive files. No model ranking, reminder effect or training-cause conclusion follows from this check.

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
