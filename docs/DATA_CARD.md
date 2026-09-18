# Data card

## Summary

The released dataset contains 72 primary agent-environment trajectories from a balanced comparison of two model endpoints, three prompt conditions, four hidden root causes, and three replicates.

## Files

- `results/*.trace.json`: 72 environment traces.
- `results/*.final.txt`: 71 final model messages. `glm__explicit__db_pool__r1` timed out before producing a final message; its complete environment trace is present.
- `results/combined_results.json`: reviewed aggregate statistics and all derived trajectory rows.
- `results/trajectory_features.csv`: flat analysis table.

## Collection

Trajectories were produced by `harness/run_incident_eval.py` against the local hidden-state simulator. Each model could call only the generated incident-control client. The run configuration fixed the CLI, reasoning setting, tool boundary, prompts, costs, timeout, and hidden-state distribution.

## Trace schema

Each trace contains:

- `metadata`: model key, provider model identifier, root cause, prompt condition, replicate, run ID, exit status, timeout flag, elapsed time, and provider usage aggregate;
- `summary`: hidden-state outcome metrics and score;
- `actions`: ordered commands, arguments, costs, observations, and selected post-action state flags;
- `written_at`: Unix timestamp.

The root cause is included in the released trace for auditability. It was unavailable to the model during the episode.

## Personal and sensitive data

The dataset contains no human subjects, user conversations, customer data, production credentials, or real infrastructure. Incident observations are synthetic.

Raw Codex JSONL event streams are excluded because they can contain ephemeral client configuration visible during execution. Published bearer tokens are not present in the traces, final messages, reports, or derived tables.

## Intended use

- reproducing the published analysis;
- auditing trajectory-level claims;
- testing alternative metrics;
- developing cost-sensitive agent evaluations;
- comparing new model endpoints under the same controlled design.

## Out-of-scope use

The dataset does not estimate performance across all software engineering, operations, research, or general agent tasks. It should not be used to infer a provider's parameter count, training compute, or internal reasoning-token budget.

## Known biases and limitations

- English tool observations with Chinese task prompts;
- one incident-response task family;
- one Codex integration;
- fixed costs and evidence order;
- three replicates per root-cause cell;
- provider endpoints may drift over time;
- usage fields follow provider accounting rather than a shared tokenizer.

## License

The released traces and derived data are distributed under the repository's [Apache License 2.0](../LICENSE).
