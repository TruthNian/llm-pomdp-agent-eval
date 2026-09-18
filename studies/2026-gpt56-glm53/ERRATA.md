# Historical validity notes — added 2026-09-18

These notes accompany the frozen v1 study. They do not replace its raw data or silently change its scores.

## Four fixed environments, repeated model runs

The `seed` field in the original `IncidentState` is stored but does not randomize the environment. The 72 trajectories are repeats over four fixed root-cause configurations, three prompt conditions and two models. They are not 72 independently generated tasks. Exact paired episode tests describe this experiment's repeated outcomes; they do not establish generalization across a broad task population.

## Root-cause key appears in the model workspace path

The original runner uses `{model}__{condition}__{root_cause}__r{replicate}` as the working-directory name. That exposes an answer-bearing label through the execution context or directory inspection. The original claim that the root-cause key was wholly unavailable to the model was too strong. This is a side channel even if a particular trajectory never visibly uses it. It weakens diagnostic-blindness claims and must be removed from future collection.

## Filesystem isolation was incomplete

The simulator runs outside the episode directory, but the old runner defaults to `danger-full-access`. A separate directory is not an access-control boundary. Source and earlier results in neighboring paths were not protected by OS isolation. The v2 remote-model adapter sends only public JSON and provides no filesystem tools; trusted local Python baselines remain an explicitly different boundary.

## Verification records invocation, not successful current-state acceptance

The v1 `deep_validated` flag is set whenever `validate deep` executes, including FAIL. Its terminal predicate checks the flag and current hidden state but does not require a passing verification after the final mutation or an explicit `finalize`. Consequently the scorer admits counterexamples such as failed validation followed by a repair without revalidation.

A direct audit of the published 72 action traces found **zero disagreements** between the recorded binary success and the stronger requirement of a later PASS after the last repair/rollback/override/alert mutation plus `finalize`. The defect matters for future evaluation even though it did not change these published binary outcomes. The v2 grader tracks successful verification by state revision and requires explicit finish; tests cover these counterexamples.

## Procedural help bundles multiple interventions

The procedural prompt supplies budget allocation, a diagnostic entry point, a stopping rule, an action order and anti-proxy requirements. Its improvement cannot isolate which component mattered. “Prompt rescue” is a valid description; a numerical intrinsic-autonomy measure or training-cause conclusion would need additional controls.

## Confidence and scope

Historical observations about particular failures remain inspectable. Claims about broad POMDP competence, parameter scale, pretraining or post-training causes need new evidence. This project now treats the initial comparison as a motivating study and prioritizes the validity of the reusable measurement system.
