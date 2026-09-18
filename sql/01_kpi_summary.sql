-- ============================================================
-- 01_kpi_summary.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   What is the overall health of the business at a glance -
--   how many orders, how much revenue/profit, what's the
--   average order value, and how are we doing operationally
--   on delivery time and order profitability?
--
-- SQL LOGIC:
--   Aggregate across the full order-item grain view. Orders are
--   counted as DISTINCT order_id (an order can have multiple
--   line items). Revenue/profit are summed at the line-item
--   grain (their natural grain). Two loss-rate metrics are
--   reported at two different grains, on purpose (see README
--   KPI Definitions):
--     loss_making_line_pct  = % of LINE ITEMS with negative profit
--     loss_making_order_pct = % of ORDERS whose profit, summed
--                              across all of that order's lines,
--                              is negative
--   These are not interchangeable and will not match numerically;
--   both are shown here to make the distinction visible at the
--   top-level KPI summary. Neither is a cancellation rate - this
--   dataset has no order_status field.
--
-- BUSINESS INTERPRETATION:
--   This is the single query an operations lead would check
--   first thing each morning. Everything else in this project
--   drills into one of these numbers.
-- ============================================================

WITH order_profit AS (
    SELECT order_id, SUM(profit) AS order_total_profit
    FROM vw_order_line_items
    GROUP BY order_id
)
SELECT
    COUNT(DISTINCT l.order_id)                                   AS total_orders,
    COUNT(*)                                                     AS total_order_lines,
    ROUND(SUM(l.sales)::numeric, 2)                              AS total_revenue,
    ROUND(SUM(l.profit)::numeric, 2)                             AS total_profit,
    ROUND(SUM(l.sales) / NULLIF(COUNT(DISTINCT l.order_id), 0), 2) AS avg_order_value,
    ROUND(AVG(l.delivery_days)::numeric, 2)                      AS avg_delivery_days,
    ROUND(
        100.0 * SUM(CASE WHEN l.is_loss_line THEN 1 ELSE 0 END) / COUNT(*), 2
    )                                                             AS loss_making_line_pct,
    (SELECT ROUND(100.0 * SUM(CASE WHEN order_total_profit < 0 THEN 1 ELSE 0 END)
                  / COUNT(*), 2) FROM order_profit)               AS loss_making_order_pct,
    ROUND(
        100.0 * SUM(l.profit) / NULLIF(SUM(l.sales), 0), 2
    )                                                             AS overall_profit_margin_pct
FROM vw_order_line_items l;

