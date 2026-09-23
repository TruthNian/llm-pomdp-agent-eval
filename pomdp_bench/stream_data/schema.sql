CREATE ROLE commerce LOGIN;
CREATE DATABASE commerce OWNER commerce;
\connect commerce
SET ROLE commerce;
CREATE TABLE orders (
    id bigserial PRIMARY KEY,
    reference text NOT NULL UNIQUE,
    revision integer NOT NULL,
    customer text NOT NULL,
    address text NOT NULL,
    items jsonb NOT NULL,
    status text NOT NULL CHECK(status IN ('draft','released','cancelled')),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE outbox (
    id bigserial PRIMARY KEY,
    event_id uuid NOT NULL UNIQUE,
    reference text NOT NULL,
    revision integer NOT NULL,
    kind text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE requests (
    request_id uuid PRIMARY KEY,
    body jsonb NOT NULL,
    response jsonb NOT NULL,
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE PUBLICATION commerce_changes FOR TABLE outbox;
