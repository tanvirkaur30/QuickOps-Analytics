-- ============================================================
-- QuickOps Analytics - PostgreSQL Schema
-- ============================================================
-- Design notes:
--   - The source data (Sample Superstore order-line export) is naturally
--     a single denormalized table: one row per product line within an order.
--   - We normalize only where it genuinely improves integrity/clarity:
--     customers, products, and locations are pulled into their own tables
--     because the same customer/product/location repeats across many rows.
--   - We do NOT over-normalize (e.g. no separate "ship_mode" or "segment"
--     lookup tables) because that would add joins without adding real value
--     for a project this size.
-- ============================================================

DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS locations CASCADE;

-- ------------------------------------------------------------
-- locations: one row per unique city/state/region combination
-- ------------------------------------------------------------
CREATE TABLE locations (
    location_id     SERIAL PRIMARY KEY,
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(100) NOT NULL,
    region          VARCHAR(50)  NOT NULL,
    country         VARCHAR(100) NOT NULL,
    postal_code     VARCHAR(20),
    UNIQUE (city, state, postal_code)
);

-- ------------------------------------------------------------
-- customers
-- ------------------------------------------------------------
CREATE TABLE customers (
    customer_id     VARCHAR(20) PRIMARY KEY,   -- source system id, e.g. CG-12520
    customer_name   VARCHAR(150) NOT NULL,
    segment         VARCHAR(50)  NOT NULL       -- Consumer / Corporate / Home Office
);

-- ------------------------------------------------------------
-- products
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id      VARCHAR(30) PRIMARY KEY,    -- source system id, e.g. FUR-BO-10001798
    product_name    VARCHAR(255) NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    sub_category    VARCHAR(50)  NOT NULL
);

-- ------------------------------------------------------------
-- orders: one row per order header (order-level attributes only)
-- ------------------------------------------------------------
CREATE TABLE orders (
    order_id        VARCHAR(20) PRIMARY KEY,    -- e.g. CA-2016-152156
    customer_id     VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    location_id     INT NOT NULL REFERENCES locations(location_id),
    order_date      DATE NOT NULL,
    ship_date       DATE NOT NULL,
    ship_mode       VARCHAR(30) NOT NULL,
    delivery_days   INT NOT NULL CHECK (delivery_days >= 0),
    CHECK (ship_date >= order_date)
);

CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_location   ON orders(location_id);
CREATE INDEX idx_orders_ship_mode  ON orders(ship_mode);

-- ------------------------------------------------------------
-- order_items: one row per product line within an order
--              (this is the original CSV's grain)
-- ------------------------------------------------------------
CREATE TABLE order_items (
    row_id          INT PRIMARY KEY,            -- source Row ID
    order_id        VARCHAR(20) NOT NULL REFERENCES orders(order_id),
    product_id      VARCHAR(30) NOT NULL REFERENCES products(product_id),
    sales           NUMERIC(12,4) NOT NULL CHECK (sales >= 0),
    quantity        INT NOT NULL CHECK (quantity > 0),
    discount        NUMERIC(4,2) NOT NULL CHECK (discount >= 0 AND discount <= 1),
    profit          NUMERIC(12,4) NOT NULL
);

CREATE INDEX idx_items_order_id   ON order_items(order_id);
CREATE INDEX idx_items_product_id ON order_items(product_id);

-- ------------------------------------------------------------
-- Convenience view: flat, analysis-ready order line items
-- (mirrors the shape analysts / BI tools usually want)
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_order_line_items AS
SELECT
    oi.row_id,
    o.order_id,
    o.order_date,
    o.ship_date,
    o.delivery_days,
    o.ship_mode,
    c.customer_id,
    c.customer_name,
    c.segment,
    l.city,
    l.state,
    l.region,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    oi.sales,
    oi.quantity,
    oi.discount,
    oi.profit,
    -- Line-item-grain flag (this view's grain is one row per product line,
    -- not per order). Do NOT read this as an order-level or cancellation
    -- flag - see sql/04_cancellation_analysis.sql and README.md for the
    -- distinction between line-level and order-level loss metrics.
    (oi.profit < 0) AS is_loss_line
FROM order_items oi
JOIN orders     o ON oi.order_id = o.order_id
JOIN customers  c ON o.customer_id = c.customer_id
JOIN locations  l ON o.location_id = l.location_id
JOIN products   p ON oi.product_id = p.product_id;
