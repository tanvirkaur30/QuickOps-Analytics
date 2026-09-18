-- ============================================================
-- 05_peak_hours.sql
-- ------------------------------------------------------------
-- ** DATASET SUBSTITUTION NOTICE **
-- The dataset stores order_date as a DATE, with no time-of-day
-- component, so true "peak hour" analysis is not possible (see
-- Dataset Availability Matrix). This file answers the closest
-- legitimate demand-timing question the data supports: peak
-- MONTH and peak DAY-OF-WEEK demand.
--
-- BUSINESS QUESTION:
--   When is demand highest across the year and across the week?
--
-- SQL LOGIC:
--   EXTRACT month and day-of-week (dow) from order_date, then
--   aggregate order counts and revenue for each.
--
-- BUSINESS INTERPRETATION:
--   Seasonal/weekly demand peaks drive staffing and inventory
--   planning decisions (e.g. pre-positioning stock ahead of a
--   known high-demand month).
-- ============================================================

-- Peak month
SELECT
    EXTRACT(MONTH FROM order_date)::int          AS order_month,
    COUNT(DISTINCT order_id)                      AS total_orders,
    ROUND(SUM(sales)::numeric, 2)                 AS total_revenue
FROM vw_order_line_items
GROUP BY order_month
ORDER BY order_month;

-- Peak day of week (0 = Sunday .. 6 = Saturday)
SELECT
    TO_CHAR(order_date, 'Day')                    AS day_of_week,
    COUNT(DISTINCT order_id)                      AS total_orders,
    ROUND(SUM(sales)::numeric, 2)                 AS total_revenue
FROM vw_order_line_items
GROUP BY day_of_week, EXTRACT(DOW FROM order_date)
ORDER BY EXTRACT(DOW FROM order_date);
