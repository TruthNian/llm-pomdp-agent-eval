# Model adapters and reproducible runs

Version 2.4 uses one HTTP transport for `chat` and `responses`. Requesting one JSON action does not require launching a native agent runtime. Both formats explicitly send `tools: []` and `tool_choice: none`; the evaluator has no external-tool dispatcher, agent subprocess or conversation-ID chain. This is a client-side contract, not attestation of a proxy or provider's hidden behavior.

From 2.6, coverage's optional `solver_assisted` condition exposes
`{"command":"solve"}` as an [environment action](DIFFICULTY.md).
It still uses the ordinary JSON response channel and empty provider tools.
Its declared public-data search consumes additional local compute, recorded
separately from model tokens; open and assisted conditions are not compute-matched.

## Offline check

```bash
python -m pomdp_bench demo --out artifacts/first-check --count 4
python -m pomdp_bench validate artifacts/first-check
```

This needs no network or model credentials. A localhost HTTP integration test additionally exercises the real `chat` adapter, including multiple turns, request projection, JSON parsing and usage accounting:

```bash
python -m unittest discover -s tests -p test_v2_runner.py -v
```

## HTTP model configuration

Copy `examples/chat-agent.example.json` to a local configuration. Supply one or more distinct names. Example:

```json
[
  {
    "name": "provider-a-model-x",
    "kind": "chat",
    "model": "your-model-id",
    "endpoint_env": "BENCH_A_ENDPOINT",
    "api_key_env": "BENCH_A_KEY",
    "timeout_seconds": 30,
    "options": {"reasoning_effort": "max", "max_completion_tokens": 4096}
  },
  {"name": "reference", "kind": "reference"}
]
```

Use options actually supported by the provider. The example does not assert that every endpoint supports `max`. Allowed request options: `temperature`, `top_p`, `max_tokens`, `max_completion_tokens`, `reasoning_effort`, `seed`. Server rejections are recorded; the adapter does not silently downgrade reasoning or remove settings. Set generous enough completion limits for your chosen reasoning mode and record them.

From 2.2, `timeout_seconds` may be any finite positive value; the previous arbitrary 60-second maximum is removed. Each request is still capped by the remaining episode wall budget. Declare the limit before collection and keep it identical across study arms. A larger timeout is an experimental setting, not a silent retry or a guarantee of remote cancellation.

From 2.5.2, the optional top-level HTTP-agent field `max_response_bytes` declares
the cumulative response-body allowance, including SSE framing and reasoning
events. It defaults to 2,000,000 bytes and accepts integers from 1 to 64,000,000.
For example, `"max_response_bytes": 16000000` permits a larger reasoning stream.
It is a local transport limit, not a provider token option or a task work budget.
Preparation freezes it; every new request audit records the effective value.
Declare it before collection and preserve failed attempts after any correction.
Old versions reject the new field; old traces without it retain their 2 MB limit.
The [2.5.1 calibration](../studies/coverage-calibration-v2/README.md) explains the
observed size failure and the subsequent local-fixture validation.

Environment variables contain the full HTTPS endpoint, such as a provider's `/v1/chat/completions` URL, and its key. Do not put secrets in command-line arguments or the configuration file. The runner records environment variable **names**, never their contents. URLs with embedded credentials, query parameters or fragments are rejected. HTTP is allowed only on loopback for local integration tests. Redirects are rejected to avoid forwarding credentials to another host.

The adapter uses a system message requiring a single JSON action, and a user message containing the complete public request. It does not expose function tools or shell execution. The benchmark is therefore evaluating the model with **this particular JSON-action harness**. It does not estimate performance of every provider's optimized agent product.

A native agent-runtime bridge can add capabilities even when this HTTP request declares none. The [2.2 pilot](../studies/verification-reserve-pilot-v1/README.md#capability-boundary-correction) retained an unexpected `imageGeneration` event: its experimental bridge disabled environment tools but omitted the independent `image_generation` switch. Rejecting such an event is not evidence that the upstream runtime had no tools. Verify effective capabilities before a new native-runtime study; keep any revised bridge and plan separate from that frozen pilot. The native bridge is not a supported portable adapter.

Accepted response body follows the common shape:

```json
{
  "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "{\"command\":\"verify\"}"}}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 8}
}
```

Reasoning usage under `completion_tokens_details.reasoning_tokens` is retained when present. Usage counts remain explicitly incomplete when unavailable. Provider error bodies, headers, reasoning text and raw responses are not written to traces. Malformed JSON terminates the episode as an adapter error; invalid but parseable actions consume environment steps. These are distinct failure modes.

From 2.3, the Chat Completions response must contain exactly one assistant choice with `finish_reason: stop`. Tool/function calls, refusal content and truncation are rejected even when the same envelope contains valid JSON text. Duplicate JSON keys and multiple JSON values are rejected. This intentionally rejects ambiguous responses previously accepted by taking the first text field. Historical traces still replay, but new collection needs a new directory and version.

## Direct Responses interface

Use [responses-agent.example.json](../examples/responses-agent.example.json) with `kind: responses` and an endpoint ending in `/responses`. Supported options are `reasoning_effort`, `max_output_tokens`, `temperature` and `top_p`; no silent conversion from Chat-specific token or seed options is performed. The declared reasoning effort maps to the protocol's `reasoning.effort` field.

Each request sends the same system instruction and complete public task/history, with `store: false`, `stream: true`, empty tools and no previous-response ID. The parser accepts a completed JSON envelope or the protocol's server-sent events. It applies only the final completed assistant message, never a text delta. Exactly one completed message containing output text is required; reasoning items are ignored rather than saved. Function calls, hosted-tool output, unrecognized events, failed/incomplete streams and missing terminal envelopes are rejected. See the official [text-generation](https://developers.openai.com/api/docs/guides/text) and [streaming](https://developers.openai.com/api/docs/guides/streaming-responses) protocol guides.

Optional `headers_env` names an environment variable containing a JSON object of distinct `X-` headers, for example a gateway's explicit exact-route selector. From 2.4 it also accepts `ChatGPT-Account-Id` for a client's explicitly supplied account selector. It cannot replace authorization, host or content headers. Values must be ASCII without control characters and are not saved to traces; never put credentials directly in configuration files. Requesting an exact route is only as reliable as the gateway implementing that header. The core does not discover login files or infer one provider's settings from another's.

### Version 2.4 protocol correction

The [second direct-channel validation](../studies/direct-channel-validation-v2/README.md) distinguishes legitimate protocol variation from tools and incomplete answers:

- A `reasoning_text` content part belongs to a declared reasoning item. It is ignored, never accumulated as action text. An output-text part must belong to a message item. Unknown parts, mixed item identities and type changes are rejected. The [official event reference](https://developers.openai.com/api/reference/resources/responses/streaming-events#response.content_part.added) documents reasoning parts; 2.3 incorrectly rejected them.
- If a streaming request receives no media header, use its declared SSE format. Do not sniff arbitrary body text. Explicit JSON envelopes are still supported when labeled as JSON.
- A native stream may finish each output item and send a final completed response with empty/omitted `output`. Assemble only closed items, require whole-response completion and exactly one valid assistant action. All started items must be closed; duplicate identities, conflicting nonempty terminal actions, unfinished streams and tool items fail. A text delta alone remains insufficient.

The local validation launcher supplies its own existing authorized login for GPT requests and the router caller key for GLM requests. This avoids changing global session-sharing state or launching a native model runtime. That machine-specific credential setup is separate from the portable adapter. Previous failures remain frozen and are not replaced by development probes.

The [2.3 direct-channel integration evidence](../studies/direct-channel-validation-v1/README.md) documents the operator's existing local router. Its small launch script supplied environment variables and used the ordinary collector. **That version did not pass multi-turn integration:** two native requests returned HTTP 401 and two GLM streams contained rejected non-text content parts. Those failures remain unchanged. The corrected protocol and authentication are evaluated separately in the [2.4 validation](../studies/direct-channel-validation-v2/README.md). The two older native bridges remain frozen experimental evidence and are not the preferred live path.

Before drawing evaluation cases, distinguish four prerequisites: the endpoint is reachable; the intended credential is authorized for that model at that endpoint; its response format satisfies the adapter contract; and multi-turn complete-history requests actually work. A catalogue listing establishes none of the last three. Check a gateway's supported authentication/sharing status without exporting credentials or silently changing global sharing. Keep any diagnostic requests separate from scored episodes. Resolve protocol differences with reviewed counterexamples before freezing a new integration plan; do not accept unknown content merely because a later text field resembles an action.

## One request deadline and inspectable failures

The shared transport has no redirects, automatic retries or implicit environment-proxy discovery. It verifies HTTPS using Python's default TLS context; an explicitly configured gateway can be the endpoint. One deadline covers the active socket exchange, including slow response headers and body reads; a deadline watchdog shuts down the local socket. DNS resolution and OS connection establishment are not an externally enforced process timeout, and local shutdown does not prove upstream cancellation. Every response is bounded by its declared byte allowance (2 MB by default), including stream bytes, and a body shorter than its declared content length is incomplete.

`request_audit` records the public request body's SHA-256, protocol, declared empty-tool policy, selected timeout, outcome code and whether a supplied response model label matches the requested string. An alias mismatch is evidence to inspect, not proof of model substitution or a silently rewritten request. No header values, credentials, provider body or reasoning is included. The hash is local provenance, not provider attestation. A crash during a request can leave only the earlier audit prefix and an in-flight checkpoint; the existing interruption rules preserve that uncertainty.

Outcome codes distinguish HTTP, transport, deadline, size, incomplete-response, unexpected-item and JSON/protocol failures. Messages say **endpoint** HTTP status because a local intermediary can generate an error itself. Reported usage from a fully received envelope is retained even when its action is rejected; absent usage remains unknown. These errors still terminate the attempt and remain in the denominator.

## Private suite, shared conditions

```bash
python -m pomdp_bench generate --fresh --count 24 --out artifacts/private/suite.json
python -m pomdp_bench run --suite artifacts/private/suite.json --agents my-agents.json --conditions open principles procedural --replicates 3 --out artifacts/experiment
python -m pomdp_bench validate artifacts/experiment
python -m pomdp_bench summarize artifacts/experiment
```

The runner executes serially and rotates agent order between cases. It never retries failed trajectories. To inspect the matrix before spending, replace `run` with `prepare`, then use `status` and `resume` on that directory. After an interruption, `resume` preserves completed results, seals any interrupted attempt as a failure, and executes only unstarted entries. Validation still requires the entire matrix. Resume requires the original core source files, framework version, Python and platform. See the [collection contract](COLLECTION.md) for commit boundaries, unknown in-flight usage and compatibility.

Model API calls cost money. Offline validation never calls a provider. Before a large collection, test one seed, inspect adapter errors and verify your model settings. Provider availability, endpoint defaults and model aliases can change: preserve provider-side snapshot IDs where available in your study notes. Current manifests capture requested configurations, not proof of an immutable provider checkpoint.

## Add a provider or policy

For a plan-bound, two-condition reminder experiment, use the [study workflow](STUDIES.md). It reuses this adapter and the same collector.

An adapter implements:

```python
class Agent:
    usage = None  # or the documented request/token counters

    def act(self, request: dict, timeout: float) -> dict:
        # request = protocol_version, task, observation, history
        return {"command": "inspect", "target": "..."}
```

Register it explicitly in `agents.py` and configuration validation. Preserve the observation allowlist, sanitize errors, represent missing usage honestly, and add an end-to-end test. Python plugins are trusted evaluator code; an untrusted executable needs separate process/OS isolation. Do not hand it the manifest or suite. Never put hidden answers in filenames, system prompts, model-visible IDs or adapter seeds.

The older Codex runner under `harness/` is retained for historical reproduction. Its system prompts and filesystem access differ from this HTTP harness. Comparing across the two requires labeling the harness change as an experimental factor.
