-- ============================================================
-- 06_average_order_value.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   How does Average Order Value (AOV) differ by customer
--   segment and region? Which segments are worth prioritizing
--   for upsell/retention efforts?
--
-- SQL LOGIC:
--   AOV must be computed at the ORDER grain, not the line-item
--   grain, so we first collapse to one row per order (summing
--   its line items) in a CTE, then average across orders.
--
-- BUSINESS INTERPRETATION:
--   AOV is a standard growth lever: businesses look at whether
--   marketing/promotions should target order frequency (more
--   orders) or basket size (bigger orders) - and this differs
--   by segment.
-- ============================================================

WITH order_totals AS (
    SELECT
        order_id,
        segment,
        region,
        SUM(sales) AS order_revenue
    FROM vw_order_line_items
    GROUP BY order_id, segment, region
)
SELECT
    segment,
    region,
    COUNT(*)                              AS total_orders,
    ROUND(AVG(order_revenue)::numeric, 2) AS avg_order_value,
    ROUND(SUM(order_revenue)::numeric, 2) AS total_revenue
FROM order_totals
GROUP BY segment, region
ORDER BY avg_order_value DESC;
