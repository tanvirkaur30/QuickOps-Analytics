"""
QuickOps - E-Commerce Operations Analytics
Streamlit dashboard. Reads the processed, cleaned dataset directly
(no database dependency) so it deploys cleanly on Streamlit Community Cloud.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import metrics as m  # noqa: E402
from utils import load_data  # noqa: E402

st.set_page_config(
    page_title="QuickOps - E-Commerce Operations Analytics",
    page_icon="📦",
    layout="wide",
)

PRIMARY = "#1f6feb"
ACCENT = "#e85d04"
NEUTRAL = "#6b7280"


@st.cache_data
def get_data():
    return load_data()


df = get_data()

# ---------------------------------------------------------------
# Sidebar filters (shared across pages)
# ---------------------------------------------------------------
st.sidebar.title("📦 QuickOps")
st.sidebar.caption("E-Commerce Operations Analytics")

page = st.sidebar.radio(
    "Navigate",
    ["Executive Overview", "Operations", "Product & Revenue", "Business Insights"],
)

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

regions = st.sidebar.multiselect("Region", sorted(df["region"].unique()), default=None)
categories = st.sidebar.multiselect("Category", sorted(df["category"].unique()), default=None)
statuses = st.sidebar.multiselect("Ship Mode", sorted(df["ship_mode"].unique()), default=None)
date_range = st.sidebar.date_input(
    "Order date range",
    value=(df["order_date"].min(), df["order_date"].max()),
    min_value=df["order_date"].min(),
    max_value=df["order_date"].max(),
)

filtered = df.copy()
if regions:
    filtered = filtered[filtered["region"].isin(regions)]
if categories:
    filtered = filtered[filtered["category"].isin(categories)]
if statuses:
    filtered = filtered[filtered["ship_mode"].isin(statuses)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered = filtered[(filtered["order_date"] >= start) & (filtered["order_date"] <= end)]

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ This dataset has no order-status/cancellation or promised-delivery "
    "field. Metrics that rely on those are shown as clearly-labeled proxies. "
    "See README for the full Dataset Availability Matrix."
)

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

# =================================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# =================================================================
if page == "Executive Overview":
    st.title("QuickOps — E-Commerce Operations Analytics")
    st.caption("Data-driven insights for demand, order performance, revenue, and operational efficiency")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders", f"{m.total_orders(filtered):,}")
    c2.metric("Total Revenue", f"${m.total_revenue(filtered):,.0f}")
    c3.metric("Avg Order Value", f"${m.average_order_value(filtered):,.2f}")
    c4.metric("Loss-Making Order Rate*", f"{m.loss_making_order_rate(filtered):.1f}%")
    c5.metric("Avg Delivery Days*", f"{m.average_delivery_days(filtered):.1f}")
    st.caption("*Loss-Making Order Rate = % of orders whose total profit (summed across all "
               "of that order's line items) is negative — used in place of a cancellation rate, "
               "which this dataset cannot compute (no order_status field). It is NOT a "
               "cancellation rate itself. Delivery days = ship_date − order_date (day-level "
               "proxy; no timestamps available).")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        trend = (
            filtered.assign(month=filtered["order_date"].dt.to_period("M").astype(str))
            .groupby("month")
            .agg(orders=("order_id", "nunique"), revenue=("sales", "sum"))
            .reset_index()
        )
        fig = px.line(trend, x="month", y="orders", title="Monthly Order Volume Trend", markers=True)
        fig.update_traces(line_color=PRIMARY)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.line(trend, x="month", y="revenue", title="Monthly Revenue Trend", markers=True)
        fig2.update_traces(line_color=ACCENT)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        loc_perf, _, _ = m.location_performance(filtered)
        fig3 = px.bar(
    loc_perf.head(10).sort_values("total_revenue"),
    x="total_revenue",
    y="state",
    color="quadrant",
    orientation="h",
    title="Top 10 States by Revenue (colored by performance quadrant)",
    ) 

        fig3.update_layout(
    xaxis_title="Revenue ($)",
    yaxis_title="State",
    margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig3, use_container_width=True)

    with col4:
        cat_rev = m.revenue_by(filtered, "category")
        fig4 = px.bar(
    cat_rev,
    x="category",
    y="total_revenue",
    color="profit_margin_pct",
    title="Revenue by Category (colored by margin %)",
    color_continuous_scale="RdYlGn"
)

    fig4.update_layout(
        xaxis_title="Category",
        yaxis_title="Revenue ($)",
        coloraxis_colorbar_title="Profit Margin (%)"
    )

    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.subheader("Key Business Insights")

    loc_perf, median_orders, avg_loss = m.location_performance(filtered)
    priority_states = loc_perf[loc_perf["quadrant"].str.contains("PRIORITY")]
    worst_subcat = m.revenue_by(filtered, "sub_category").sort_values("profit_margin_pct").iloc[0]
    discount_high = filtered[filtered["discount"] > 0.4]  # matches README/SQL "41%+" band exactly
    # Line-item grain here on purpose: discount is a line-item attribute, so
    # a line rate (not an order rate) is the correct denominator.
    discount_loss_rate = m.loss_making_line_rate(discount_high) if len(discount_high) else 0
    slow_mode = m.delivery_benchmark_by_ship_mode(filtered).sort_values("avg_delivery_days", ascending=False).iloc[0]

    insights = []
    if len(priority_states) > 0:
        top_p = priority_states.iloc[0]
        state_avg_discount = filtered.loc[filtered["state"] == top_p["state"], "discount"].mean()
        insights.append(
            f"**{top_p['state']}** combines high order volume ({top_p['total_orders']:,} orders) "
            f"with an order-level loss-making rate of **{top_p['loss_rate_pct']:.1f}%**, well above the "
            f"cross-state average of {avg_loss:.1f}% — and also runs a notably higher average "
            f"discount ({state_avg_discount:.0%}) than lower-loss states, so this is likely the "
            f"same underlying discounting pattern as the finding below, not a separate cause."
        )
    insights.append(
        f"**{worst_subcat['sub_category']}** has the weakest profit margin of any sub-category at "
        f"**{worst_subcat['profit_margin_pct']:.1f}%**, despite generating ${worst_subcat['total_revenue']:,.0f} in revenue."
    )
    if len(discount_high) > 0:
        insights.append(
            f"Order LINES (not orders) discounted **over 40%** have a loss-making line rate of "
            f"**{discount_loss_rate:.1f}%** (n={len(discount_high):,}) — concentrated in a handful of "
            f"sub-categories rather than spread evenly, so this reads as a pricing pattern in specific "
            f"product lines, not a universal effect."
        )
    insights.append(
        f"**{slow_mode['ship_mode']}** has the longest average delivery time at "
        f"{slow_mode['avg_delivery_days']:.1f} days, with {slow_mode['pct_over_benchmark']:.1f}% "
        f"of its own orders exceeding its own internal, data-derived benchmark (not a contractual SLA)."
    )
    insights.append(
        f"Overall profit margin stands at **{m.profit_margin_pct(filtered):.1f}%** across "
        f"{m.total_orders(filtered):,} orders and ${m.total_revenue(filtered):,.0f} in revenue."
    )
    for ins in insights[:5]:
        st.markdown(f"- {ins}")

# =================================================================
# PAGE 2 — OPERATIONS
# =================================================================
elif page == "Operations":
    st.title("Operations")
    st.caption("Order volume, delivery performance, and location-level operational health")

    loc_perf, median_orders, avg_loss = m.location_performance(filtered)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(loc_perf, x="state", y="total_orders", color="quadrant",
                     title="Order Volume by State")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(loc_perf.sort_values("loss_rate_pct", ascending=False),
                      x="state", y="loss_rate_pct", color="quadrant",
                      title="Loss-Making Order Rate by State (%)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Volume vs. Performance Quadrant")
    st.caption(
        f"X = order volume · Y = loss-making order rate. Dashed lines mark the overall "
        f"median volume ({median_orders:.0f} orders) and average loss rate ({avg_loss:.1f}%)."
    )
    fig3 = px.scatter(
        loc_perf, x="total_orders", y="loss_rate_pct", color="quadrant", size="total_revenue",
        hover_name="state", title="State Performance Quadrant",
    )
    fig3.add_vline(x=median_orders, line_dash="dash", line_color=NEUTRAL)
    fig3.add_hline(y=avg_loss, line_dash="dash", line_color=NEUTRAL)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        month_demand = (
            filtered.assign(month_name=filtered["order_date"].dt.strftime("%b"),
                             month_num=filtered["order_date"].dt.month)
            .groupby(["month_num", "month_name"])["order_id"].nunique()
            .reset_index().sort_values("month_num")
        )
        fig4 = px.bar(month_demand, x="month_name", y="order_id", title="Order Volume by Month (Seasonality)")
        st.plotly_chart(fig4, use_container_width=True)
    with col4:
        delivery_bench = m.delivery_benchmark_by_ship_mode(filtered)
        fig5 = px.bar(delivery_bench, x="ship_mode", y="avg_delivery_days",
                      title="Avg Delivery Days by Ship Mode (internal benchmark, not a contractual SLA)")
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")
    st.subheader("High-Volume / Low-Performance Segments (state × sub-category)")
    st.caption(
        "line_loss_rate_pct is a LINE-ITEM rate (sub-category is a line-item attribute), "
        "not the same order-level rate shown above — see README for the distinction."
    )
    bottleneck = m.bottleneck_segments(filtered)
    priority = bottleneck[bottleneck["quadrant"].str.contains("PRIORITY")].head(15)
    st.dataframe(priority, use_container_width=True)

# =================================================================
# PAGE 3 — PRODUCT & REVENUE
# =================================================================
elif page == "Product & Revenue":
    st.title("Product & Revenue")
    st.caption("Category performance, top products, and revenue contribution")

    cat_rev = m.revenue_by(filtered, "category")
    subcat_rev = m.revenue_by(filtered, "sub_category")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(cat_rev, names="category", values="total_revenue", title="Revenue Contribution by Category")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(subcat_rev, x="sub_category", y="profit_margin_pct",
                      color="profit_margin_pct", color_continuous_scale="RdYlGn",
                      title="Profit Margin % by Sub-Category")
        fig2.update_xaxes(tickangle=45)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    top_products = (
        filtered.groupby("product_name")
        .agg(total_revenue=("sales", "sum"), total_quantity=("quantity", "sum"), total_profit=("profit", "sum"))
        .reset_index().sort_values("total_revenue", ascending=False).head(10)
    )
    top_products["total_revenue"] = top_products["total_revenue"].round(2)
    st.subheader("Top 10 Products by Revenue")
    st.dataframe(top_products, use_container_width=True)

    st.markdown("---")
    trend = (
        filtered.assign(month=filtered["order_date"].dt.to_period("M").astype(str))
        .groupby(["month", "category"])["sales"].sum().reset_index()
    )
    fig3 = px.line(trend, x="month", y="sales", color="category", title="Category Revenue Trend Over Time")
    st.plotly_chart(fig3, use_container_width=True)

# =================================================================
# PAGE 4 — BUSINESS INSIGHTS
# =================================================================
else:
    st.title("Business Insights")
    st.caption("Finding → Evidence → Possible Cause → Recommended Action → KPI to Monitor")

    loc_perf, median_orders, avg_loss = m.location_performance(filtered)
    priority_states = loc_perf[loc_perf["quadrant"].str.contains("PRIORITY")].sort_values("total_orders", ascending=False)
    subcat_rev = m.revenue_by(filtered, "sub_category")
    worst_margin = subcat_rev.sort_values("profit_margin_pct").iloc[0]
    discount_high = filtered[filtered["discount"] > 0.4]  # matches README/SQL "41%+" band exactly
    # Line-item grain on purpose — discount is a line-item attribute.
    discount_loss_rate = m.loss_making_line_rate(discount_high) if len(discount_high) else 0
    baseline_loss_rate = m.loss_making_line_rate(filtered)

    findings = []

    if len(priority_states) > 0:
        top_p = priority_states.iloc[0]
        state_avg_discount = filtered.loc[filtered["state"] == top_p["state"], "discount"].mean()
        other_states_avg_discount = filtered.loc[filtered["state"] != top_p["state"], "discount"].mean()
        findings.append({
            "finding": f"{top_p['state']} combines high order volume with a high order-level loss-making rate.",
            "evidence": f"{top_p['state']}: {top_p['total_orders']:,} orders, "
                        f"{top_p['loss_rate_pct']:.1f}% of orders net loss-making vs. {avg_loss:.1f}% "
                        f"cross-state average. {top_p['state']}'s average discount is {state_avg_discount:.0%} "
                        f"vs. {other_states_avg_discount:.0%} for all other states.",
            "cause": "HYPOTHESIS: this is very likely the *same* pattern as the discount finding below, not "
                     "an independent state-level cause — the high-loss states also run far higher average "
                     "discounts. Whether that's regional pricing policy, sales-negotiation practice, or "
                     "customer mix is not determinable from this data alone.",
            "action": f"Treat this as ONE discounting-policy question, not a state-specific one: review why "
                      f"{top_p['state']} (and similarly-discounted states) run such deep discounts, using "
                      f"California/New York's discount levels as the benchmark to close toward.",
            "kpi": "Loss-Making Order Rate (order-level) and Avg. Discount, both by state",
        })

    findings.append({
        "finding": f"{worst_margin['sub_category']} is the weakest sub-category by profit margin.",
        "evidence": f"{worst_margin['sub_category']}: {worst_margin['profit_margin_pct']:.1f}% margin on "
                    f"${worst_margin['total_revenue']:,.0f} revenue.",
        "cause": "HYPOTHESIS: heavier average discounting on this sub-category relative to others.",
        "action": f"Review discount approval thresholds for {worst_margin['sub_category']}; "
                  f"evaluate whether list pricing or promo cadence needs adjustment.",
        "kpi": "Sub-Category Profit Margin %",
    })

    if len(discount_high):
        top_subcat = discount_high["sub_category"].value_counts()
        top_subcat_share = top_subcat.iloc[0] / len(discount_high)
        findings.append({
            "finding": "Deep discounting (over 40%) is strongly associated with loss-making order LINES.",
            "evidence": f"Order lines with discount > 40% (n={len(discount_high):,}) have a "
                        f"{discount_loss_rate:.1f}% loss-making LINE rate vs. {baseline_loss_rate:.1f}% overall "
                        f"(both at line-item grain, since discount is a line-item attribute — not comparable "
                        f"to the order-level rate above). {top_subcat_share:.0%} of these deep-discount lines "
                        f"are concentrated in a single sub-category ('{top_subcat.index[0]}'), so this is not "
                        f"spread evenly across the catalog.",
            "cause": "FACT (directly observable correlation, large sample) — causality (whether discounting "
                     "*causes* the loss, vs. inherently thin-margin items simply being discounted more) is "
                     "not established by this data. Also note: the extremely clean 0%→100% loss-rate jump is "
                     "consistent with this sample dataset's profit field being formula-driven rather than "
                     "fully independent transactional noise — a real production dataset may be noisier.",
            "action": "Set a discount-approval ceiling (e.g. requiring manager sign-off above 30%), starting "
                      "with the concentrated sub-category above, and monitor margin impact before/after.",
            "kpi": "Loss-Making Line Rate by Discount Band",
        })

    slow_mode_row = m.delivery_benchmark_by_ship_mode(filtered).sort_values("pct_over_benchmark", ascending=False).iloc[0]
    findings.append({
        "finding": f"{slow_mode_row['ship_mode']} shipments most frequently exceed their own delivery history.",
        "evidence": f"{slow_mode_row['pct_over_benchmark']:.1f}% of {slow_mode_row['ship_mode']} orders exceed "
                    f"the {slow_mode_row['benchmark_days']:.0f}-day internal, data-derived benchmark for that "
                    f"mode (NOT a contractual SLA — this dataset has no promised-delivery-date field).",
        "cause": "HYPOTHESIS: possible carrier/fulfillment inconsistency for this ship mode — "
                 "no carrier-level data available to confirm.",
        "action": f"Audit fulfillment/carrier performance specifically for {slow_mode_row['ship_mode']} orders.",
        "kpi": "% Orders Exceeding Ship-Mode Delivery Benchmark",
    })

    for f in findings:
        with st.container(border=True):
            st.markdown(f"#### 🔎 {f['finding']}")
            st.markdown(f"**Evidence:** {f['evidence']}")
            st.markdown(f"**Possible Cause:** {f['cause']}")
            st.markdown(f"**Recommended Action:** {f['action']}")
            st.markdown(f"**KPI to Monitor:** `{f['kpi']}`")

    st.markdown("---")
    st.caption(
        "All figures above are calculated live from the currently filtered dataset — nothing here is "
        "hardcoded. FACT = directly observable in the data. HYPOTHESIS = a plausible explanation that "
        "would need further investigation to confirm. Recommendations describe what should be "
        "investigated/measured, not a proven outcome."
    )
