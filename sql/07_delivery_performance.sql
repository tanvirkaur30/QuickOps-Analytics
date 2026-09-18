-- ============================================================
-- 07_delivery_performance.sql
-- ------------------------------------------------------------
-- ** DATASET SUBSTITUTION NOTICE **
-- There is no "promised delivery date" field, so a true
-- promised-vs-actual On-Time Delivery Rate cannot be computed
-- (see Dataset Availability Matrix). Instead, this file derives
-- an INTERNAL, DATA-DERIVED BENCHMARK per ship mode from the
-- data's own history (the 75th percentile of that ship mode's
-- own delivery_days), and flags orders that exceed their own
-- mode's typical benchmark. This is explicitly NOT a contractual
-- SLA and does not represent any promise made to a customer -
-- it is a self-referential "slower than usual for this mode"
-- signal only.
--
-- BUSINESS QUESTION:
--   How long does delivery actually take by shipping mode, and
--   which orders are unusually slow relative to their own mode's
--   historical norm?
--
-- SQL LOGIC:
--   A window function computes each ship_mode's 75th-percentile
--   delivery_days as an internal, data-derived benchmark;
--   individual orders above that benchmark are flagged as slower
--   than their own mode's historical norm.
--
-- BUSINESS INTERPRETATION:
--   Comparing actual delivery time against the shipping mode's
--   own normal behavior — rather than a fixed number or a
--   promised date we don't have — reveals which shipments are
--   underperforming their own historical standard.
-- ============================================================

WITH benchmarks AS (
    SELECT
        ship_mode,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY delivery_days) AS p75_days
    FROM vw_order_line_items
    GROUP BY ship_mode
),
order_level AS (
    SELECT DISTINCT order_id, ship_mode, delivery_days
    FROM vw_order_line_items
)
SELECT
    ol.ship_mode,
    COUNT(*)                                                        AS total_orders,
    ROUND(AVG(ol.delivery_days)::numeric, 2)                        AS avg_delivery_days,
    ROUND(b.p75_days::numeric, 2)                                   AS internal_benchmark_days,
    SUM(CASE WHEN ol.delivery_days > b.p75_days THEN 1 ELSE 0 END)  AS orders_over_benchmark,
    ROUND(
        100.0 * SUM(CASE WHEN ol.delivery_days > b.p75_days THEN 1 ELSE 0 END)
        / COUNT(*), 2
    )                                                                AS pct_over_benchmark
FROM order_level ol
JOIN benchmarks b ON ol.ship_mode = b.ship_mode
GROUP BY ol.ship_mode, b.p75_days
ORDER BY avg_delivery_days DESC;
