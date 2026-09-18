-- ============================================================
-- 08_location_performance.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   Which states combine high order volume with poor
--   operational/commercial performance (high order-level loss
--   rate, slow delivery)? These are the operational priorities.
--
-- SQL LOGIC:
--   Grain: ORDER-LEVEL. A state either fulfilled a given order
--   profitably or it didn't, so profit is first summed across
--   all of an order's line items (order_profit CTE), and THEN
--   the sign of that total is checked - this is not the same
--   number as a line-item loss rate (see
--   sql/04_cancellation_analysis.sql and sql/10_operational_
--   bottlenecks.sql, which are deliberately line-item-grain
--   instead, because their unit of analysis - discount band,
--   sub-category - is a line-item attribute, not an order
--   attribute). A CTE computes the overall (all-state) average
--   order-level loss rate and median order volume, then a CASE
--   WHEN flags states that are both above-median volume AND
--   above-average loss rate.
--
-- BUSINESS INTERPRETATION:
--   This is the query behind the volume-vs-performance quadrant
--   used in the bottleneck framework (see 10_operational_bottlenecks.sql
--   and README "Operational Bottleneck Framework"). This is a
--   loss-making ORDER rate, not a cancellation rate - this
--   dataset has no order_status field.
-- ============================================================

WITH order_profit AS (
    -- Collapse to one row per order: state (constant per order - every
    -- order ships to exactly one state) and total profit across all of
    -- that order's line items.
    SELECT
        order_id,
        state,
        region,
        SUM(sales)  AS order_revenue,
        SUM(profit) AS order_profit,
        AVG(delivery_days) AS delivery_days   -- constant per order; AVG just collapses duplicates
    FROM vw_order_line_items
    GROUP BY order_id, state, region
),
state_stats AS (
    SELECT
        state,
        region,
        COUNT(*)                                                       AS total_orders,
        ROUND(SUM(order_revenue)::numeric, 2)                          AS total_revenue,
        ROUND(
            100.0 * SUM(CASE WHEN order_profit < 0 THEN 1 ELSE 0 END) / COUNT(*), 2
        )                                                               AS order_loss_rate_pct,
        ROUND(AVG(delivery_days)::numeric, 2)                          AS avg_delivery_days
    FROM order_profit
    GROUP BY state, region
),
overall AS (
    SELECT
        AVG(order_loss_rate_pct) AS avg_loss_rate,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_orders) AS median_orders
    FROM state_stats
)
SELECT
    s.*,
    CASE
        WHEN s.total_orders >= o.median_orders AND s.order_loss_rate_pct >= o.avg_loss_rate
            THEN 'High Volume / Poor Performance - PRIORITY'
        WHEN s.total_orders >= o.median_orders AND s.order_loss_rate_pct < o.avg_loss_rate
            THEN 'High Volume / Good Performance - BENCHMARK'
        WHEN s.total_orders < o.median_orders AND s.order_loss_rate_pct >= o.avg_loss_rate
            THEN 'Low Volume / Poor Performance - INVESTIGATE'
        ELSE 'Low Volume / Good Performance - LOW PRIORITY'
    END AS performance_segment
FROM state_stats s
CROSS JOIN overall o
ORDER BY s.total_orders DESC;

