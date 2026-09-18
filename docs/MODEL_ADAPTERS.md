# Model adapters and reproducible runs

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

Environment variables contain the full HTTPS endpoint, such as a provider's `/v1/chat/completions` URL, and its key. Do not put secrets in command-line arguments or the configuration file. The runner records environment variable **names**, never their contents. URLs with embedded credentials, query parameters or fragments are rejected. HTTP is allowed only on loopback for local integration tests. Redirects are rejected to avoid forwarding credentials to another host.

The adapter uses a system message requiring a single JSON action, and a user message containing the complete public request. It does not expose function tools or shell execution. The benchmark is therefore evaluating the model with **this particular JSON-action harness**. It does not estimate performance of every provider's optimized agent product.

Accepted response body follows the common shape:

```json
{
  "choices": [{"message": {"content": "{\"command\":\"verify\"}"}}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 8}
}
```

Reasoning usage under `completion_tokens_details.reasoning_tokens` is retained when present. Usage counts remain explicitly incomplete when unavailable. Provider error bodies, headers, reasoning text and raw responses are not written to traces. Malformed JSON terminates the episode as an adapter error; invalid but parseable actions consume environment steps. These are distinct failure modes.

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
