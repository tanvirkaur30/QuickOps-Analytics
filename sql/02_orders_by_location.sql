-- ============================================================
-- 02_orders_by_location.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   Which regions/states generate the highest order volume and
--   revenue? Where is demand concentrated?
--
-- SQL LOGIC:
--   Group by region and state, count distinct orders, sum
--   revenue, and rank states within each region using a window
--   function (RANK) so we can see the top state per region
--   without a second query.
--
-- BUSINESS INTERPRETATION:
--   Demand concentration tells the business where fulfillment
--   capacity (warehouses, staffing, inventory) matters most.
-- ============================================================

SELECT
    region,
    state,
    COUNT(DISTINCT order_id)                       AS total_orders,
    ROUND(SUM(sales)::numeric, 2)                  AS total_revenue,
    RANK() OVER (PARTITION BY region ORDER BY SUM(sales) DESC) AS rank_within_region
FROM vw_order_line_items
GROUP BY region, state
ORDER BY region, total_revenue DESC;
