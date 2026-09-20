# Format-feedback follow-up

One additional complete GLM-route episode is fixed by [plan.json](plan.json),
under framework 2.9.1. It follows the preserved
[original incident collection](../settlement-incident-v1/README.md), in which the
old parser terminated GLM after 13 applied actions. This is an integration
validation, not a fresh model comparison or a replacement of that failure.

Completed malformed assistant action text now consumes a rejected environment
step and exposes format feedback on the next turn. No action is guessed; no
transport retry occurs. Envelope and transport failures remain terminal.
Local wire tests exercise both recovery to successful business delivery and
persistent invalid output exhausting the finite action budget.

The environment, public task, reasoning effort, action budget and request/wall
limits are unchanged. Only this episode's source/version and adapter recovery
semantics differ. Collection is pending; results must be recorded before drawing
any claim about the live route.
