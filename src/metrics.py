"""
metrics.py
----------
Reusable KPI functions for QuickOps. Used by both the Jupyter EDA notebook
and the Streamlit dashboard (app.py) so KPI logic is defined exactly once.

Every function is documented with its formula. Only metrics genuinely
supported by the dataset are implemented - see README's Dataset
Availability Matrix for what was excluded and why.

All functions accept a pandas DataFrame at the order-LINE-ITEM grain
(one row per product line, matching data/processed/orders_clean.csv)
unless noted otherwise.
"""

import pandas as pd


def total_orders(df: pd.DataFrame) -> int:
    """Count of distinct orders (an order may have multiple line items)."""
    return df["order_id"].nunique()


def total_revenue(df: pd.DataFrame) -> float:
    """Sum of sales across all order line items."""
    return round(df["sales"].sum(), 2)


def total_profit(df: pd.DataFrame) -> float:
    return round(df["profit"].sum(), 2)


def average_order_value(df: pd.DataFrame) -> float:
    """AOV = Total Revenue / Total Orders (order grain, not line-item grain)."""
    orders = total_orders(df)
    return round(total_revenue(df) / orders, 2) if orders else 0.0


def profit_margin_pct(df: pd.DataFrame) -> float:
    """Overall profit margin = Total Profit / Total Revenue * 100."""
    rev = df["sales"].sum()
    return round(100 * df["profit"].sum() / rev, 2) if rev else 0.0


def loss_making_line_rate(df: pd.DataFrame) -> float:
    """
    % of order LINE ITEMS with negative profit (line-item grain).
    Used wherever the analysis itself is naturally at the line-item grain
    (e.g. by discount band, by sub-category) — discount and sub-category
    are line-item attributes, so a line-item rate is the correct grain
    there, not an approximation of an order-level rate.
    NOT a cancellation-rate metric: this dataset has no order_status field.
    See loss_making_order_rate() for the order-grain version used in
    location/bottleneck analysis.
    """
    if len(df) == 0:
        return 0.0
    return round(100 * (df["profit"] < 0).sum() / len(df), 2)


def loss_making_order_rate(df: pd.DataFrame) -> float:
    """
    % of DISTINCT ORDERS whose total profit (summed across all of that
    order's line items) is negative. This is the order-grain version,
    used wherever the unit of analysis is the order itself (e.g. by
    state/location) rather than an individual product line.
    Proxy for order-level operational/commercial failure, used in place
    of an unavailable cancellation-rate metric (no order_status field
    exists in this dataset) — this is NOT a cancellation rate.
    """
    order_profit = df.groupby("order_id")["profit"].sum()
    if len(order_profit) == 0:
        return 0.0
    return round(100 * (order_profit < 0).sum() / len(order_profit), 2)


def average_delivery_days(df: pd.DataFrame) -> float:
    """
    Mean of (ship_date - order_date) in days.
    Day-level proxy for delivery/fulfillment time; the dataset has no
    order-time or promised-delivery-date fields, so this is not a true
    quick-commerce delivery-time metric (which would be in minutes).
    """
    return round(df["delivery_days"].mean(), 2)


def delivery_benchmark_by_ship_mode(df: pd.DataFrame) -> pd.DataFrame:
    """
    Internal, DATA-DERIVED delivery benchmark: the 75th percentile of
    delivery_days FOR EACH ship mode, computed from this dataset's own
    history. This is NOT a contractual SLA and does not represent a
    promise made to any customer — there is no promised-delivery-date
    field in this dataset. Orders slower than their own mode's benchmark
    are flagged as exceeding it.
    """
    order_level = df.drop_duplicates(subset="order_id")
    bench = (
        order_level.groupby("ship_mode")["delivery_days"]
        .quantile(0.75)
        .rename("benchmark_days")
        .reset_index()
    )
    merged = order_level.merge(bench, on="ship_mode")
    merged["breaches_benchmark"] = merged["delivery_days"] > merged["benchmark_days"]
    summary = (
        merged.groupby("ship_mode")
        .agg(
            total_orders=("order_id", "count"),
            avg_delivery_days=("delivery_days", "mean"),
            benchmark_days=("benchmark_days", "first"),
            pct_over_benchmark=("breaches_benchmark", lambda s: round(100 * s.mean(), 2)),
        )
        .reset_index()
    )
    summary["avg_delivery_days"] = summary["avg_delivery_days"].round(2)
    return summary



def revenue_by(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Generic revenue/profit/order-count rollup by any categorical column."""
    out = (
        df.groupby(group_col)
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("sales", "sum"),
            total_profit=("profit", "sum"),
        )
        .reset_index()
    )
    out["total_revenue"] = out["total_revenue"].round(2)
    out["total_profit"] = out["total_profit"].round(2)
    out["profit_margin_pct"] = (
        100 * out["total_profit"] / out["total_revenue"]
    ).round(2)
    return out.sort_values("total_revenue", ascending=False)


def location_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Order volume + ORDER-LEVEL loss rate + delivery time by state,
    classified into a 4-quadrant operational-priority framework.

    Grain choice: the business unit here is the ORDER (a state either
    fulfilled a given order profitably or it didn't) — so loss is computed
    by first summing profit across all of an order's line items, THEN
    checking whether that total is negative. This differs from
    loss_making_line_rate(), which is appropriate for line-item-level
    analyses (e.g. by discount band) where the line item, not the order,
    is the natural unit.

    Methodology:
      X axis = order volume (vs. overall median across states)
      Y axis = order-level loss rate (vs. overall average across states)
    """
    stats = (
        df.groupby(["state", "region"])
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("sales", "sum"),
            avg_delivery_days=("delivery_days", "mean"),
        )
        .reset_index()
    )
    # Order-level loss: sum profit per order first, then evaluate sign.
    order_totals = df.groupby(["order_id", "state"])["profit"].sum().reset_index()
    loss = (
        order_totals.groupby("state")
        .apply(lambda g: round(100 * (g["profit"] < 0).sum() / len(g), 2), include_groups=False)
        .rename("loss_rate_pct")
        .reset_index()
    )
    stats = stats.merge(loss, on="state")
    stats["total_revenue"] = stats["total_revenue"].round(2)
    stats["avg_delivery_days"] = stats["avg_delivery_days"].round(2)

    median_orders = stats["total_orders"].median()
    avg_loss_rate = stats["loss_rate_pct"].mean()

    def classify(row):
        high_vol = row["total_orders"] >= median_orders
        poor_perf = row["loss_rate_pct"] >= avg_loss_rate
        if high_vol and poor_perf:
            return "High Volume / Poor Performance - PRIORITY"
        if high_vol and not poor_perf:
            return "High Volume / Good Performance - BENCHMARK"
        if not high_vol and poor_perf:
            return "Low Volume / Poor Performance - INVESTIGATE"
        return "Low Volume / Good Performance - LOW PRIORITY"

    stats["quadrant"] = stats.apply(classify, axis=1)
    return stats.sort_values("total_orders", ascending=False), median_orders, avg_loss_rate


def bottleneck_segments(df: pd.DataFrame, min_orders: int = 5) -> pd.DataFrame:
    """
    Finer-grained (state x sub_category) bottleneck detection.
    Same quadrant methodology as location_performance(), applied at a
    finer grain to pinpoint specific hot spots rather than whole states.

    Grain choice: this is deliberately computed at the LINE-ITEM grain
    (not order-level, unlike location_performance()). sub_category is a
    line-item attribute — a single order can contain multiple
    sub-categories — so "order-level loss for a given sub-category" isn't
    a well-defined concept the way "order-level loss for a given state" is
    (every order has exactly one ship-to state, but can span several
    sub-categories). The column is named line_loss_rate_pct to make this
    grain explicit rather than implying it's comparable to
    location_performance()'s order-level loss_rate_pct.

    Segments with fewer than `min_orders` distinct orders are excluded
    to avoid flagging statistical noise.
    """
    stats = (
        df.groupby(["state", "sub_category"])
        .agg(
            order_volume=("order_id", "nunique"),
            total_profit=("profit", "sum"),
        )
        .reset_index()
    )
    loss = (
        df.groupby(["state", "sub_category"])
        .apply(lambda g: round(100 * (g["profit"] < 0).sum() / len(g), 2), include_groups=False)
        .rename("line_loss_rate_pct")
        .reset_index()
    )
    stats = stats.merge(loss, on=["state", "sub_category"])
    stats = stats[stats["order_volume"] >= min_orders]
    stats["total_profit"] = stats["total_profit"].round(2)

    median_vol = stats["order_volume"].median()
    avg_loss = stats["line_loss_rate_pct"].mean()

    def classify(row):
        high_vol = row["order_volume"] >= median_vol
        poor_perf = row["line_loss_rate_pct"] >= avg_loss
        if high_vol and poor_perf:
            return "High Volume / Poor Performance - PRIORITY"
        if high_vol and not poor_perf:
            return "High Volume / Good Performance - BENCHMARK"
        if not high_vol and poor_perf:
            return "Low Volume / Poor Performance - INVESTIGATE"
        return "Low Volume / Good Performance - LOW PRIORITY"

    stats["quadrant"] = stats.apply(classify, axis=1)
    return stats.sort_values(["order_volume"], ascending=False)
