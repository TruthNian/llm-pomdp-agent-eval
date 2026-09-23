# Commerce operations

The service accepts draft orders, amendments, cancellations, and release instructions.
A successful response is an acknowledgement of the customer's request. Released
orders must be booked with the carrier exactly once, with the accepted address and
line items. Draft and cancelled orders must not be dispatched. Order history must
continue to reflect accepted requests. Request IDs support retrying a command;
reusing an ID with different content is a conflict. Database numeric IDs are internal.

`POST /commands` takes `request_id` (UUID), `reference`, `revision` (a positive
customer-supplied sequence), and `kind` (`draft`, `amend`, `release`, `cancel`). Draft
and amendment commands also contain `customer`, `address`, and `items`. Each item
contains `sku`, `quantity`, and `unit_cents`. A release or cancellation applies to
the current draft. The service rejects changes to released or cancelled orders.
`GET /orders/{reference}` returns the current order; `/health` reports API liveness.

Normal release-to-carrier latency is at most 60 seconds. During an incident, brief
maintenance is preferable to lost or duplicate shipments. Restore acceptance,
history and processing of accepted releases before handing over. A paused consumer
or an empty queue alone does not establish that customers' work has been completed.

Deployment configuration lives under `/etc/commerce`. Application processes use
Supervisor. Logs are under `/var/log/commerce`. PostgreSQL and Kafka retain their
ordinary runtime state under `/var/lib`. The application implementation, schema,
and carrier integration notes are deployed with the service. Standard administration
tools remain available. Carrier operations are through its merchant HTTP API.
