# Orders service

The HTTP service accepts orders and serves customer order history. The business
reference belongs to the customer; the database id is an internal surrogate.
An accepted order must remain available with its original customer, delivery
address and line items. Retrying the same reference and body returns the existing
order; reusing a reference with different content is a conflict. Preserve accepted
orders during operational maintenance. Brief maintenance is preferable to losing
customer records; resume normal acceptance and history before handing over.

`POST /orders` accepts `reference`, `customer`, `address`, and a nonempty `items`
array. Items contain `sku`, positive integer `quantity`, and nonnegative integer
`unit_cents`. The response includes an internal `order_id`. `GET /orders/{reference}`
returns the order. A successful write must become readable within 30 seconds under
normal load. `/health` is process liveness, not a business reconciliation check.

The application loads `config.json` on every request. PostgreSQL owns the data;
`schema.sql` describes the relational layout. Services run under Supervisor. Deployment
files live here; normal process and database logs are under `/var/log`.
