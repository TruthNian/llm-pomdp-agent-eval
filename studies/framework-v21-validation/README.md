# Framework 2.1 collection validation

This is an implementation and integration check, **not a model ranking or mechanism study**. It validates P1 of the [development roadmap](../../docs/ROADMAP.md). [机器可读证据](validation.json) records every planned episode, including the failed request.

## Offline acceptance

- 52 unit/integration tests passed, including real process termination, competing collectors, failure retention, commit-boundary recovery, source drift, pre-call plan tampering and divergent checkpoint histories.
- The clean-source offline demo at commit `bb2f888` produced 32 episodes: the public-information reference accepted 8/8; random, overdiagnosis and proxy controls each accepted 0/8. Every episode replayed.
- The new validator also replayed the existing 576-episode 2.0 control collection. All 156 frozen historical files and the original 72-trace dataset passed their integrity checks.
- [Cross-platform CI at the tested core revision](https://github.com/TruthNian/llm-pomdp-agent-eval/actions/runs/35329753720) passed Windows/Linux and Python 3.11/3.13.

The controls are implementation checks and deliberately designed failure policies. They do not calibrate frontier-model performance.

## Live local-model pilot

The collector fixed four episodes before calling either model: one development seed (`41`), `diagnosis` and `cascade`, standard profile, incident skin, open condition, one replicate, and both configured models. There was no outcome-based exclusion or replacement.

| Requested model | Family | Accepted | Durable steps | Action cost | Termination |
|---|---|---:|---:|---:|---|
| GPT-5.6 Sol | diagnosis | yes | 4 | 12 | explicit finish |
| GPT-5.6 Sol | cascade | yes | 11 | 32 | explicit finish |
| GLM-5.3 through the existing local router | diagnosis | yes | 6 | 14 | explicit finish |
| GLM-5.3 through the existing local router | cascade | no | 7 | 17 | local bridge timeout / adapter error |

All four records passed full matrix and trajectory validation. The bridge completed 28 requests and failed one of 29. That failed request exhausted the bridge's event wait, resulting in local HTTP 502; this does **not** establish that the upstream provider itself returned 502. It is an integration failure, not an adjudicated inability to solve the task. The failed episode remains in the denominator. Its complete token total is unknown; observed earlier counters are retained as partial evidence.

Both models were requested at `high` reasoning. HTTP request timeout was 60 seconds, the bridge event wait was 52 seconds, and each episode had a 600-second wall budget. Identically named reasoning settings do not mean identical compute. One development seed supplies no meaningful population uncertainty or model-ranking evidence.

## Harness and provenance

The regular Python `chat` adapter called an authenticated loopback bridge. The bridge used the installed [Codex app-server protocol](https://learn.chatgpt.com/docs/app-server) and existing local sign-ins, without extracting or saving provider credentials. Each action used a fresh ephemeral model context containing the full public benchmark history. Environment access and dynamic tools were empty; shell, browser, apps, plugins and delegation features were disabled. Unexpected completed tool items were rejected by the bridge.

The local Codex runtime also reported global GitHub-operation instructions: prefer `gh`, use HTTPS and use the existing credential helper without revealing tokens. They contained no benchmark data. This extra runtime context means the pilot is not identical to a direct provider HTTP experiment. Its instruction fingerprint and observed reasoning settings are recorded in [validation.json](validation.json).

The exact local bridge implementation is preserved as a [non-executable source snapshot](bridge_snapshot.py.txt). It is an experimental evidence artifact, not a supported portable adapter. It depends on the installed experimental app-server fields and the operator's two existing model/provider registrations. Native transport behavior and provider-side checkpoint identity were not independently attested. No remote cancellation or complete billing claim is made for the timed-out request.

Collection began with an uncommitted working tree based on `04c7513`. Its complete core source fingerprints were subsequently verified byte-for-byte against committed revision `fde1703d1a226ef9e39287b7a1e3e826ea4df60b`; the original dirty flag and recorded revision are preserved. The later `bb2f888` change strengthens checkpoint-prefix validation and passes on these same four traces. An initial bridge startup configuration error happened before manifest creation and model requests; it was corrected before the sole four-episode collection.

Public evidence includes all four terminal outcomes, partial/complete usage counters, request status metadata and source fingerprints. Private manifests, checkpoint files, credentials, raw provider responses and model reasoning are not published. These results close the local integration check for P1; they do not close P2's mechanism-identification or P4's external-validity gates.
