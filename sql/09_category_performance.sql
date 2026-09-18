-- ============================================================
-- 09_category_performance.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   Which sub-categories are high revenue but low/negative
--   margin, i.e. quietly draining profitability while looking
--   good on a revenue-only dashboard?
--
-- SQL LOGIC:
--   Rank sub-categories by revenue and separately by margin
--   using two window functions (RANK), then surface the ones
--   where the two ranks diverge sharply (top-10 revenue but
--   bottom-10 margin).
--
-- BUSINESS INTERPRETATION:
--   This is a classic quick-commerce/retail trap: chasing GMV
--   (revenue) while margin erodes through discounting. Category
--   managers need both numbers side by side, not just revenue.
-- ============================================================

WITH cat_stats AS (
    SELECT
        sub_category,
        category,
        ROUND(SUM(sales)::numeric, 2)                         AS total_revenue,
        ROUND(SUM(profit)::numeric, 2)                        AS total_profit,
        ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct
    FROM vw_order_line_items
    GROUP BY sub_category, category
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
        RANK() OVER (ORDER BY margin_pct ASC)      AS margin_rank_worst_first
    FROM cat_stats
)
SELECT *
FROM ranked
ORDER BY revenue_rank;
