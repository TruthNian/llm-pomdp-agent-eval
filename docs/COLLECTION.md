# Collection, interruption and compatibility

Framework 2.1 keeps `diagnostic-graphs/1`, protocol/schema 1 and the existing prompts, transitions and task acceptance unchanged. It adds a versioned collection contract and the explicit `collection_interrupted` termination. Do not pool 2.0 and 2.1 records as one study.

## Smallest operational workflow

```bash
python -m pomdp_bench generate --count 2 --seed 0 --out artifacts/private/dev-suite.json
python -m pomdp_bench prepare --suite artifacts/private/dev-suite.json --agents examples/agents.json --out artifacts/collection
python -m pomdp_bench status artifacts/collection
python -m pomdp_bench resume artifacts/collection
python -m pomdp_bench validate artifacts/collection
```

`run` remains the convenience form of `prepare` followed by `resume`. A fresh output directory is required for preparation. `prepare` is an execution plan, **not** scientific preregistration: hypotheses, primary contrasts and data-dependent stopping rules still need a study protocol. Preparation and status make no model calls.

The manifest freezes cases, configurations, conditions, replicates, budget, software and an ordered schedule fingerprint. The schedule deterministically rotates agent order by case, preserving 2.0 ordering. Preparation shows the episode count so an accidentally large matrix can be noticed before paid calls.

## One attempt, durable evidence

| File | Role |
|---|---|
| `private/manifest.json` | Fixed execution definition, suite and source fingerprints |
| `private/manifest.sha256.json` | Preparation-time fingerprint, checked before the first attempt too |
| `private/starts/EPISODE.json` | Write-once start, bound to the manifest fingerprint |
| `private/checkpoints/EPISODE.json` | Latest atomic public trajectory snapshot and request-boundary flag |
| `private/traces/EPISODE.json` | Write-once terminal evidence |
| `private/receipts/EPISODE.json` | Write-once commitment to the terminal trace and manifest |
| `summary.json` | Rebuildable report after complete evidence validation |

There is one start per scheduled episode, without a retry loop. Atomic replacement and file flush protect checkpoints from ordinary process interruption. An advisory OS lock permits one collector and is released when the process exits; no PID-age guess or manual lock-file deletion is needed. Use local storage with normal OS lock/rename semantics. This is not a guarantee against disk failure, network-filesystem behavior, malicious edits or a power cut across multiple metadata writes.

## Recovery rules

1. Validate every existing trace, checkpoint, start and receipt before making a call. Refuse unexpected episodes, altered definitions, mismatched hashes or missing receipted traces.
2. Preserve completed traces byte-for-byte, including adapter errors and timeouts. If only a receipt is missing after a crash, validate and seal the existing trace.
3. If an attempt has a terminal checkpoint but no trace, preserve its terminal outcome. This includes an already accepted `finish`.
4. If an attempt has a nonterminal checkpoint, replay its last durable public history and seal it as `collection_interrupted`. Do not ask the model for the missing action or restart the episode. A start with no checkpoint is conservatively recorded as an interrupted attempt with no durable actions.
5. Execute only entries with no start record, under the original configuration.
6. Require the complete scheduled matrix and all receipts before writing a summary.

Persist a request-boundary checkpoint before every `act` call and another after processing its result. If a process dies after the provider accepted the request, the response and its bill may be unknown. The flag means a request **may** have been in flight, not proof that the provider billed it. Recovery sets usage to null for interrupted episodes, retains last observed counters in `partial_usage`, and labels recorded elapsed time as a lower bound. Completed environment actions after the last durable checkpoint cannot be reconstructed and are not invented.

Environment action costs are measured on the durable simulated trajectory; they do not estimate lost provider spend. Collection failures are shown separately from adapter failures while both remain in the success denominator. A resumed experiment affected by outages should not be interpreted as a clean model-capability comparison without an explicit study-level treatment of that outage.

Storage failures stop collection instead of being converted to model errors. Keyboard interruption also stops collection; `resume` performs the explicit recovery later. A stopped collector must actually exit before a new collector starts. HTTP deadlines do not guarantee remote request cancellation.

## Versions and remaining limits

Historical 2.0 traces/manifests can still be validated and summarized, using the unchanged environment contract. They cannot be resumed: they lack request-boundary evidence. Retrieve the 2.0 release when reproducing its original collection runtime.

2.1 resume requires identical framework/collection versions, core source bytes, Python and platform strings. Documentation-only changes do not block it. A different runtime starts a new study directory. Summaries refuse mixed framework versions; they do not infer compatibility merely because final success predicates look similar.

Environment variable values are not stored or fingerprinted. Requested model names and settings are recorded, but a mutable provider alias, changed endpoint behind an environment variable, provider-side prompt handling or checkpoint migration can still change serving behavior. Pin provider-side versions where possible and document any changes. This release does not claim immutable provider-checkpoint attestation.

The evidence is private by default. Do not publish the private directory during collection or expose it to model tools. Review seeds, configurations, identifiers and error metadata before exporting a retired run. No automatic retry, cross-runtime migration, distributed locking, automatic raw-run export or billing reconciliation is implemented.
