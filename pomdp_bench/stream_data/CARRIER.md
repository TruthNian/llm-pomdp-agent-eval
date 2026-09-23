# Parcel merchant API, revision 1

The configured endpoint accepts `POST /bookings` with an `Idempotency-Key` header
and JSON fields `client_reference`, `order_reference`, `customer`, `address`, `items`.
The client reference is merchant metadata; it is not a uniqueness constraint.
One order may have multiple legitimate parcels. A repeated key with identical
content returns the original booking (200); changed content returns 409. A new
key creates a booking (201). Successful booking commits a consignment to the
carrier's dispatch ledger. This API does not offer deletion or cancellation of
committed consignments. Application database changes do not alter that ledger.

`GET /bookings` returns the merchant's bookings in creation order. Optional
`order_reference` and `client_reference` query parameters filter that list. Responses
include the original content, `booking_id`, `idempotency_key`, and `accepted_at`.
`GET /health` reports API liveness. All amounts and parcel contents are local test
data in this deployment; the service has no connection to a commercial carrier.
