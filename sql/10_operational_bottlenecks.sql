-- ============================================================
-- 10_operational_bottlenecks.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   Across states AND sub-categories, where should operations
--   focus attention first? (This is the master bottleneck query
--   that the "Operational Bottlenecks" dashboard page and the
--   Business Insights page are built from.)
--
-- METHODOLOGY (documented, not arbitrary):
--   1. Compute two axes per (state, sub_category) combination:
--        X = order volume        (how much this segment matters)
--        Y = loss-making LINE rate (how poorly it's performing)
--   2. Compare each combination against the OVERALL median volume
--      and OVERALL average loss rate (computed once, in a CTE).
--   3. Classify into the same 4-quadrant framework used at the
--      state level in 08_location_performance.sql, but at a
--      finer grain (state x sub-category) to pinpoint specific
--      operational hot spots rather than whole states.
--   4. Only combinations with a minimum sample size (>= 5 orders)
--      are included, to avoid flagging noise from tiny segments.
--
-- GRAIN NOTE (important - differs from 08 on purpose):
--   08_location_performance.sql uses an ORDER-level loss rate
--   (sum profit per order, then check the sign) because state is
--   a well-defined, one-per-order attribute. Here, sub_category
--   is a LINE-ITEM attribute - a single order can span several
--   sub-categories - so "this order's loss, attributed to this
--   sub-category" isn't well-defined. This file therefore uses a
--   LINE-ITEM loss rate instead (line_loss_rate_pct), which is
--   the correct grain for a sub-category-level metric, not an
--   inconsistency with 08.
--
-- SQL LOGIC:
--   CTEs + window functions (PERCENTILE_CONT for median, plain
--   AVG for the loss-rate benchmark), then a CASE WHEN quadrant
--   classifier - same classification logic as 08, at a finer,
--   line-item grain.
--
-- BUSINESS INTERPRETATION:
--   "High Volume / Poor Performance" rows are the highest-ROI
--   places for an operations team to investigate first: they
--   affect the most orders AND are underperforming. This is a
--   loss-making LINE rate, not a cancellation rate - this
--   dataset has no order_status field.
-- ============================================================

WITH segment_stats AS (
    SELECT
        state,
        sub_category,
        COUNT(DISTINCT order_id)                                        AS order_volume,
        ROUND(
            100.0 * SUM(CASE WHEN is_loss_line THEN 1 ELSE 0 END) / COUNT(*), 2
        )                                                                AS line_loss_rate_pct,
        ROUND(SUM(profit)::numeric, 2)                                  AS total_profit
    FROM vw_order_line_items
    GROUP BY state, sub_category
    HAVING COUNT(DISTINCT order_id) >= 5      -- ignore statistically thin segments
),
overall AS (
    SELECT
        AVG(line_loss_rate_pct)                                     AS avg_loss_rate,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_volume)   AS median_volume
    FROM segment_stats
)
SELECT
    s.state,
    s.sub_category,
    s.order_volume,
    s.line_loss_rate_pct,
    s.total_profit,
    ROUND(o.median_volume::numeric, 1)  AS overall_median_volume,
    ROUND(o.avg_loss_rate::numeric, 2)  AS overall_avg_line_loss_rate,
    CASE
        WHEN s.order_volume >= o.median_volume AND s.line_loss_rate_pct >= o.avg_loss_rate
            THEN 'High Volume / Poor Performance - PRIORITY'
        WHEN s.order_volume >= o.median_volume AND s.line_loss_rate_pct < o.avg_loss_rate
            THEN 'High Volume / Good Performance - BENCHMARK'
        WHEN s.order_volume < o.median_volume AND s.line_loss_rate_pct >= o.avg_loss_rate
            THEN 'Low Volume / Poor Performance - INVESTIGATE'
        ELSE 'Low Volume / Good Performance - LOW PRIORITY'
    END AS quadrant
FROM segment_stats s
CROSS JOIN overall o
ORDER BY
    CASE
        WHEN s.order_volume >= o.median_volume AND s.line_loss_rate_pct >= o.avg_loss_rate THEN 0
        ELSE 1
    END,
    s.order_volume DESC;

