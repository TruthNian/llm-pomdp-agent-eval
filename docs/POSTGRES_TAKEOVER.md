# PostgreSQL incident takeover — evaluator notes

Framework 2.13; generator `incident-takeover/1`; runtime `docker-postgres/1`.
This file, the launcher and the evaluator are never installed in the agent container.
The user-approved [design](INCIDENT_TAKEOVER.md) governs future candidates too.

## Causal construction and provenance

The agent receives only a customer symptom, the recovery goal, `/srv/orders`, root authorization
inside the sandbox and the generic `exec`/`finish` transport. It can discover ordinary source,
configuration, process logs, a pre-incident backup, installed tools and PostgreSQL documentation.
There is no private-state verify command, risk menu, recovery hint or mandatory prescribed self-check.

Two real PostgreSQL 18 processes begin as primary and physical standby. Twenty accepted orders
replicate. The standby is promoted; the old primary accepts 45 additional orders. The application
then writes 25 orders to the new primary while still reading the old primary. Independent sequence
allocation produces overlapping internal IDs, checked from actual HTTP receipts during construction.
These are different business references and line items, not simulated corruption flags.

The causal inspiration is GitHub's [October 2018 incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/):
divergent accepted writes make failback a data-preservation problem. That incident used MySQL.
This is a constructed PostgreSQL adaptation with a small order API, **not a production reproduction**.
[PostgreSQL's pg_rewind contract](https://www.postgresql.org/docs/current/app-pgrewind.html) describes
resynchronizing diverged clusters; it does not merge business records from both branches.
Both database processes share one container/kernel; no claim of a reproduced distributed network outage.

Noise comes from real process lifecycle, replication, customer reads/writes and health traffic.
No fabricated log corpus or unrelated extra fault is added. The candidate still has a small topology;
real software alone does not establish frontier difficulty.

## Execution, observations and acceptance

The target has no host bind mounts, engine socket, provider credentials or external network.
It has a 1 GiB memory limit, two CPUs and 256 processes. A separate read-only customer container
shares only its network namespace. The evaluator and accepted-order receipts live on the host.
The model may edit code/configuration/data, use native help, create backups or pause services.
Native command errors and warnings are returned without evaluator annotation.

The workload starts before the first model request: one new order, one historical read and one
health request, then ten seconds of real time before the next batch. It continues during inference
and scripts. It is not an action tick or adversarially adjusted schedule. Actual timing and responses
are recorded; maintenance failures are reported separately from final delivery. Provisioning and
terminal checks are included in elapsed time. Handover ends model interaction; audit results never
enter its observation history.

Terminal audit stops the workload, submits six fresh orders, retrieves every initially or subsequently
accepted reference, checks identical retry and conflicting-reference behavior, restarts the target
without restoring data, and retrieves all accepted orders again. Acceptance requires correct customer,
address and line items, new writes, idempotency and persistence. The internal numeric ID is not a business
identity and may change. No particular topology or repair command is required. Brief maintenance is
allowed by the discoverable ordinary service contract. Unobserved orders, infinite future durability
and all possible API inputs are not claimed to have been tested.

Observer/initialization/provider failures do not establish cognitive difficulty. The grader recomputes
business results from receipts/responses rather than trusting a stored PASS. Recorded replay checks
bindings and grades without execution. Fresh execution has different clocks, logs and workload timing;
it must be reported separately, never called byte-identical replay.

## Qualification and ceiling gate

`tools/qualify_takeover.py` executes four **known-solution artifact controls**, not blind reference policies:
untouched, routing-only, rewind without merging, and preserving/merging by business reference with
foreign-key remapping. Routing-only leaves 45 old-branch orders unavailable. Actual rewind removes
those old-only records from the old database too. This demonstrates destructive resynchronization,
not a proof that every conceivable forensic recovery is impossible. A surviving ordinary pre-incident
backup contains only the common prefix. The complete merge restores all accepted records and survives restart.

The [original text-channel attempts](../studies/incident-takeover-v1/README.md) ended with adapter
failures. A separately frozen [native-tool Sol max screen](../studies/incident-takeover-native-v1/README.md)
on the unchanged environment delivered in 9/150 actions and preserved all 110 accepted orders through
restart. Seventeen reads and seventeen writes failed during permitted maintenance. The preregistered
rejection rule applies: retain this candidate as a regression anchor, not high-difficulty evidence.
Do not make it harder by hiding ordinary useful tools, adding secret requirements or withholding
the original business goal. Future failures require causal audit and a public-information
counterfactual before any difficulty claim.

## Run locally

Docker Engine is required; Linux or WSL2 is supported. The Windows development installation stores
WSL, its Ubuntu distribution and Docker data on E:. Docker Desktop is not needed. Create a private
JSON config with `docker_command` argv (normally `["docker"]`). For WSL use the WSL prefix followed
by `docker`, and `keepalive_command` with the same prefix followed by `cat`; its open stdin keeps
the distribution alive while the runtime owns it. No credentials belong in this file.

For a local Linux Docker installation, first create `artifacts/takeover-docker.json`
with `{"docker_command":["docker"]}`. For the E-drive Windows/WSL installation used here:

```json
{
  "docker_command": ["E:/Apps/WSL/wsl.exe", "-d", "CodexBench", "-u", "root", "--", "docker"],
  "keepalive_command": ["E:/Apps/WSL/wsl.exe", "-d", "CodexBench", "-u", "root", "--", "cat"]
}
```

Adjust executable paths and distribution names to your installation. The builder fills the image
and asset bindings. Use a fresh local file when building; preserve prior study configurations.

```bash
python -m tools.build_takeover artifacts/takeover-docker.json
export POMDP_TAKEOVER_CONFIG="$PWD/artifacts/takeover-docker.json"
python -m tools.qualify_takeover artifacts/takeover-controls
```

In PowerShell, use `$env:POMDP_TAKEOVER_CONFIG = (Resolve-Path artifacts/takeover-docker.json).Path`
in place of the `export` line. Qualification executes four known-solution controls, without model calls.

For a fresh model attempt, copy the [native-tool example](../examples/takeover-agent.example.json),
set its model ID and provider-supported reasoning effort, and supply `BENCH_RESPONSES_ENDPOINT`
(the full Responses endpoint) and `BENCH_API_KEY` through environment variables as described in
[model adapters](MODEL_ADAPTERS.md). Keep credentials out of JSON files and the repository.
The example is a configuration template, not a reproduced study or a held-out task.

```bash
python -m pomdp_bench prepare-takeover-suite --out artifacts/takeover-suite.json
python -m pomdp_bench run --suite artifacts/takeover-suite.json --agents examples/takeover-agent.example.json --out artifacts/takeover-run --wall-seconds 3600
python -m pomdp_bench validate artifacts/takeover-run
```

Use unused output paths. The run command makes real model requests; validation only regrades retained
observations and bindings. To inspect the published result without invoking a model or Docker, run
`python studies/incident-takeover-native-v1/verify.py` instead.

The builder binds normalized asset hashes and an immutable image ID. The base digest is pinned;
apt repository contents are not a promise of byte-identical future image builds. Archive the built
image for identical runtime reuse. Study preparation checks the declared image and assets before
collection. The existing collector records all package source hashes and the complete attempt.
