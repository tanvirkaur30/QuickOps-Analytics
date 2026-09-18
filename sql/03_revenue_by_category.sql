-- ============================================================
-- 03_revenue_by_category.sql
-- ------------------------------------------------------------
-- BUSINESS QUESTION:
--   Which categories and sub-categories generate the most
--   revenue, and does high revenue also mean high profit?
--
-- SQL LOGIC:
--   Group by category + sub-category. Compute both revenue and
--   profit margin so that revenue leaders and margin leaders
--   can be compared side by side (they are often different).
--
-- BUSINESS INTERPRETATION:
--   A category can be a top revenue driver while quietly losing
--   money on margin (common when discounting is heavy). This
--   query is what makes that visible.
-- ============================================================

SELECT
    category,
    sub_category,
    COUNT(*)                                              AS total_line_items,
    ROUND(SUM(sales)::numeric, 2)                         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)                        AS total_profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS profit_margin_pct,
    ROUND(AVG(discount)::numeric, 3)                      AS avg_discount
FROM vw_order_line_items
GROUP BY category, sub_category
ORDER BY total_revenue DESC;
