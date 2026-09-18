# Adapting the benchmark

This guide explains how to compare other models or create new task families without destroying the benchmark's causal structure.

## Replace the two model endpoints

The default analysis expects two short keys, `gpt` and `glm`. Override their provider model identifiers without editing source:

```bash
python harness/run_incident_eval.py \
  --model-spec gpt=provider/model-a \
  --model-spec glm=provider/model-b \
  --models gpt,glm \
  --conditions open,explicit,procedural \
  --replicates 3
```

You can register another key for data collection:

```bash
python harness/run_incident_eval.py \
  --model-spec candidate=provider/model-c \
  --models candidate \
  --conditions open \
  --replicates 1
```

`analyze_results.py` currently performs paired comparisons only for keys named `gpt` and `glm`. Rename or generalize those arms before producing a new two-model report.

## Preserve pairing

Every compared model must receive the same combination of:

- prompt condition;
- hidden root cause;
- replicate index;
- action costs and total budget;
- timeout and tool boundary.

Pairing is what allows the exact discordance test to distinguish stable direction from aggregate-rate noise.

## Preserve hidden-state blindness

The root cause and simulator implementation must remain outside the model-readable directory. The generated run directory should contain only:

- the task description;
- the narrow `envctl.py` client;
- files intentionally supplied as observations.

Do not copy `incident_server.py`, result traces, answer keys, or prior runs into the episode directory.

## Add a new root cause

Update all of the following together:

1. `ROOT_CAUSES` in `incident_server.py`;
2. the decoy mapping;
3. root-specific logs, metrics, and probe behavior;
4. the correct remediation;
5. `DECISIVE` in `analyze_results.py`;
6. balancing and expected-count checks in `tools/verify_release.py`;
7. documentation of the new latent state.

A useful root cause needs at least:

- one cheap but incomplete clue;
- one high-value direct observation;
- one plausible distractor;
- one unique correct remediation;
- a post-repair observation change.

## Change the budget

Maintain the key feasibility relation:

```text
diagnostic allowance = total budget - remediation cost - strong validation cost
```

If all actions remain affordable after exhaustive diagnosis, the environment no longer tests stop discipline. If the correct path is infeasible even with an optimal policy, failures cease to be interpretable.

Randomized-cost studies should sample costs before the episode and expose the realized price schedule to the model.

## Add a prompt condition

Add the prompt to `PROMPTS` and keep all environment variables fixed. Describe exactly which control layer the prompt adds:

- goal content;
- general principle;
- decision rule;
- budget allocation;
- stop condition;
- action sequence;
- anti-proxy constraint.

Prompt ablations are strongest when each condition changes one policy component.

## Compare reasoning settings

Use `--reasoning-effort` and run a complete balanced design for every setting. Treat reasoning setting as a new experimental factor; do not mix settings inside one model-condition cell.

```bash
python harness/run_incident_eval.py --reasoning-effort high ...
```

Record the provider's exposed setting and the CLI command. Hidden reasoning-token availability is a product property unless the research question explicitly controls inference compute.

## Avoid common validity failures

- Do not score the final message for success.
- Do not reveal the remaining optimal action sequence.
- Do not let the agent modify simulator or scorer code.
- Do not add a distractor that accidentally becomes predictive of the root cause.
- Do not compare unmatched root-cause or prompt distributions.
- Do not silently rerun only failed trajectories.
- Do not publish raw event streams containing transient credentials.
- Do not interpret cross-provider results as a parameter-count ablation.

## Recommended extensions

- Randomize action costs and evidence order.
- Create non-incident task skins with the same latent decision graph.
- Add environments where proxy manipulation can fool a weak evaluator.
- Track human corrections, restarts, and review time.
- Report accepted completions per token and per unit of human supervision.
- Compare base-compatible checkpoints before and after post-training.
