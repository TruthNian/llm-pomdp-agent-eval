CREATE ROLE orders LOGIN;
CREATE DATABASE orders OWNER orders;
\connect orders
SET ROLE orders;
CREATE TABLE orders (
    id bigserial PRIMARY KEY,
    reference text NOT NULL UNIQUE,
    customer text NOT NULL,
    address text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE lines (
    order_id bigint NOT NULL REFERENCES orders(id),
    line_no integer NOT NULL,
    sku text NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_cents integer NOT NULL CHECK (unit_cents >= 0),
    PRIMARY KEY (order_id, line_no)
);
