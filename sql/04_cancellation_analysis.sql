-- ============================================================
-- 04_cancellation_analysis.sql
-- ANALYSIS NAME (corrected): Profitability / Commercial-Risk
-- Line Analysis — retained under this filename/number to match
-- the project's original 01-10 numbering and README references,
-- but the analysis itself is NOT a cancellation analysis.
-- ------------------------------------------------------------
-- ** DATASET SUBSTITUTION NOTICE **
-- This dataset has NO order_status / cancellation field, so a
-- true cancellation-rate query cannot be built (see the Dataset
-- Availability Matrix in README.md). This file does not measure,
-- imply, or approximate cancellations. It answers a different,
-- fully-supported question instead: which line items lose money
-- (profit < 0), and where that concentrates by segment and
-- discount level. "Loss-making" here means "this line item's
-- profit is negative" - nothing more, nothing about order status.
--
-- BUSINESS QUESTION:
--   What share of order LINE ITEMS lose money, and where is that
--   concentrated (segment, discount level)?
--
-- SQL LOGIC:
--   is_loss_line (line-item grain flag, profit < 0) is already
--   derived in the view. Aggregate the loss-making LINE rate by
--   segment and by discount band using a CASE WHEN bucket. This
--   is deliberately a LINE-ITEM rate, not an order-level rate -
--   discount is a line-item attribute, so a single order can mix
--   several discount levels across its lines. See
--   src/metrics.py::loss_making_line_rate() and README.md's KPI
--   Definitions for the line-vs-order distinction.
--
-- BUSINESS INTERPRETATION:
--   A high loss-making LINE rate concentrated in one segment or
--   discount band points to a pricing/discounting policy pattern
--   worth investigating - this is a correlational signal, not
--   proof that discounting causes the loss (see README's FACT
--   vs. HYPOTHESIS framing and the sub-category concentration
--   caveat there).
-- ============================================================

SELECT
    segment,
    CASE
        WHEN discount = 0            THEN '0% (no discount)'
        WHEN discount <= 0.2         THEN '1-20%'
        WHEN discount <= 0.4         THEN '21-40%'
        ELSE '41%+'
    END                                                     AS discount_band,
    COUNT(*)                                                AS total_line_items,
    SUM(CASE WHEN is_loss_line THEN 1 ELSE 0 END)           AS loss_making_lines,
    ROUND(
        100.0 * SUM(CASE WHEN is_loss_line THEN 1 ELSE 0 END) / COUNT(*), 2
    )                                                        AS loss_making_line_rate_pct,
    ROUND(SUM(profit)::numeric, 2)                          AS net_profit
FROM vw_order_line_items
GROUP BY segment, discount_band
ORDER BY loss_making_line_rate_pct DESC;

