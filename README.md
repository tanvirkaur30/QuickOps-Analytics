# QuickOps — E-Commerce Operations Analytics

A business/operations analytics project: take a messy order dataset, find what's
actually wrong with the business, separate proven facts from hypotheses, and
recommend specific, measurable actions.

**DATA → ANALYSIS → INSIGHT → ACTION → KPI** — not DATA → ML MODEL → ACCURACY.

Built for an Associate Program Manager / Business Operations application.

---

## Business Problem

> How can an e-commerce business use operational data to identify bottlenecks,
> understand demand patterns, monitor performance, and improve efficiency?

## Objective

Demonstrate the full analyst workflow: SQL + Python analysis → KPI definition →
bottleneck identification → an internal dashboard → evidence-based
recommendations with a way to measure whether they worked.

---

## Dataset

| | |
|---|---|
| **Name** | Sample – Superstore (order-line export) |
| **Rows / Columns (raw)** | 9,994 rows × 21 columns |
| **Grain** | One row per product line item within an order (5,009 distinct orders) |
| **Date range** | Jan 2014 – Dec 2017 |
| **Geography** | United States (49 states, 531 cities, 4 regions) |
| **Source used in this project** | Public GitHub mirror of the widely-used "Sample Superstore" dataset (originally distributed by Tableau as sample/training data and re-hosted in hundreds of public data-analytics repos and Kaggle listings for education) |
| **License / usage** | Long-standing free public sample dataset used across the BI/data-analytics community for training and portfolio projects; no PII (customer names are synthetic sample data, not real people) |

**Actual raw columns:** `Row ID, Order ID, Order Date, Ship Date, Ship Mode,
Customer ID, Customer Name, Segment, Country, City, State, Postal Code,
Region, Product ID, Category, Sub-Category, Product Name, Sales, Quantity,
Discount, Profit`

### Why this dataset

I looked for a real quick-commerce dataset with true order-status/cancellation
fields and minute-level delivery timestamps (to match a Blinkit-style
business). None of the datasets reachable from this environment's network
had both. Rather than fabricate columns to make the project *look* like
quick-commerce, I used the closest legitimate substitute — a real,
well-documented e-commerce order dataset — and was explicit everywhere about
which metrics are directly supported vs. derived proxies. **Analytical
honesty was prioritized over surface-level thematic fit.**

---

## Dataset Availability Matrix

This matrix is what actually determined which KPIs and SQL files were built.

| Business Metric | Required Columns | Available? | Derivable? | Decision |
|---|---|---|---|---|
| Total Orders / Revenue | `Order ID`, `Sales` | Yes | — | **Implement** |
| Average Order Value | `Sales`, `Order ID` | Yes | Yes | **Implement** |
| Profit / Margin | `Profit`, `Sales` | Yes | — | **Implement** |
| **Cancellation Rate** | `order_status` | **No** | No | **Exclude.** No cancellation metric exists anywhere in this project. Replaced with two clearly-separate proxies: **Loss-Making Order Rate** (order grain — sum profit per order, then check the sign) for location/bottleneck analysis, and **Loss-Making Line Rate** (line-item grain) for discount/sub-category analysis, since those analyses' unit is the line item, not the order. Neither is a cancellation rate. |
| **Delivery Time (actual)** | `Order Date`, `Ship Date` | Yes | Yes (day-level only) | **Implement**, but as `delivery_days` — a day-level proxy. The dataset has no timestamps, so this is not a true quick-commerce (minute-level) delivery-time metric. |
| **Promised Delivery Time / On-Time Rate** | a promised-date field | **No** | No | **Exclude true SLA.** Replaced with an **internal, data-derived benchmark per Ship Mode** (75th percentile of that mode's own delivery days) — explicitly NOT a contractual SLA, since no promise-to-customer field exists. |
| Orders by Location | `City`, `State`, `Region` | Yes | — | **Implement** |
| Revenue by Category | `Category`, `Sub-Category` | Yes | — | **Implement** |
| **Peak Hours (time of day)** | `order_time` | **No** | No | **Exclude.** Dataset only has order *dates*. Replaced with **peak month / day-of-week** demand analysis. |
| Customer Segmentation | `Segment` | Yes (segment only, no demographics) | — | **Implement** at Segment level only |
| Discount Impact on Profit | `Discount`, `Profit` | Yes | Yes | **Implement** |

**Bottom line:** cancellation and true delivery-SLA analysis are the two
requested analyses this dataset cannot honestly support. Both were replaced
with clearly-labeled proxy metrics rather than invented fields — this
substitution is called out again at the top of `sql/04_cancellation_analysis.sql`
(renamed internally to a Profitability / Commercial-Risk Line Analysis — the
filename/number is kept only for consistency with this project's 01–10
numbering), `sql/05_peak_hours.sql`, and `sql/07_delivery_performance.sql`.

---

## Business Questions Answered

- Which states/regions generate the highest order volume and revenue?
- Which states combine high volume with poor performance (the bottleneck question)?
- Which categories/sub-categories drive revenue — and do they also drive profit?
- Which customer segments have the highest average order value?
- When does demand peak across the year and the week?
- Does discount depth relate to order profitability?
- How does delivery time differ by shipping mode, and which mode most often exceeds its own historical norm?

---

## Tech Stack & Architecture

```
Raw CSV (Sample Superstore)
        ↓
Data Cleaning & Validation   (src/data_cleaning.py)
        ↓
PostgreSQL                   (sql/schema.sql, src/data_loading.py)
        ↓
SQL Analysis                 (sql/01–10, tested against a live Postgres instance)
        ↓
Python EDA                   (notebooks/01_eda.ipynb)
        ↓
Reusable KPI / Metrics Layer (src/metrics.py — shared by the notebook and the dashboard)
        ↓
Streamlit Dashboard          (app.py)
        ↓
Business Insights & Recommendations
```

**Stack:** Python, Pandas, NumPy, SQL, PostgreSQL, Jupyter, Plotly, Streamlit,
Git. Nothing else.

### Why NOT React / FastAPI / Docker / Kubernetes / Kafka / ML

| Requirement | What would justify it | Why it wasn't used here |
|---|---|---|
| React | Highly custom, complex client-side interactivity | An analytics dashboard is Streamlit's exact use case — full custom UI adds implementation time without adding business value here |
| FastAPI | A separate backend serving multiple clients | This project has one consumer (the dashboard); no separate API is needed |
| Docker | Reproducible, multi-service environments | Streamlit Community Cloud deploys directly from the repo; no orchestration problem to solve |
| Kubernetes | Scaling many containerized services | Wildly out of scope for a single analytics app |
| Kafka | Real-time event streams | This is historical, batch data — there is no stream to consume |
| Machine Learning | A genuine prediction/classification/forecasting requirement | The objective is descriptive + diagnostic analytics (what happened, why, what to do) — not prediction |

The point being demonstrated: **choose tools based on the business problem,
not to make the stack look impressive.**

---

## Data Cleaning

Run: `python src/data_cleaning.py`

What was actually found and fixed in **this** dataset (see full log in
`src/data_cleaning.py` docstrings and printed report):

- Column names standardized to snake_case (labels only, no value changes).
- **0** exact duplicate rows, **0** missing values, **0** invalid numeric
  ranges — verified programmatically, not assumed.
- `Order Date` / `Ship Date` parsed from strings to real `datetime` types.
- Logical check: `ship_date >= order_date` (holds for all 9,994 rows) — a
  `data_quality_flag` column is added rather than silently dropping any
  future violation.
- Derived `delivery_days = ship_date − order_date` and `is_loss_line =
  profit < 0` — both are simple, transparent derivations from existing raw
  columns, not fabricated fields.

Output: `data/processed/orders_clean.csv` (9,994 rows × 24 columns).

---

## SQL Analysis

All 10 files in `sql/` were written against, and **tested by executing
against, a live local PostgreSQL 16 instance** (not just syntax-checked).
Each file's header documents its business question, SQL logic, and business
interpretation.

| File | Question | Notable SQL |
|---|---|---|
| `01_kpi_summary.sql` | Overall business health | Aggregate functions, `NULLIF` guards |
| `02_orders_by_location.sql` | Where is demand concentrated? | `RANK() OVER (PARTITION BY ...)` |
| `03_revenue_by_category.sql` | Revenue vs. margin by category | `GROUP BY`, ratio calculations |
| `04_cancellation_analysis.sql` *(substituted — see below)* | Loss-making LINE patterns by segment/discount | `CASE WHEN` discount bucketing |
| `05_peak_hours.sql` *(substituted)* | Peak month / day-of-week demand | `EXTRACT()`, `TO_CHAR()` |
| `06_average_order_value.sql` | AOV by segment/region | CTE to collapse to order grain first |
| `07_delivery_performance.sql` *(substituted)* | Delivery time by ship mode + internal benchmark (not SLA) | `PERCENTILE_CONT`, window join |
| `08_location_performance.sql` | State-level bottleneck quadrant (order-level loss rate) | CTEs, `PERCENTILE_CONT`, `CASE WHEN` classifier |
| `09_category_performance.sql` | Revenue leaders vs. margin leaders | Two independent `RANK()` window functions |
| `10_operational_bottlenecks.sql` | **Master bottleneck query** (state × sub-category, line-item loss rate) | CTEs + window functions + minimum-sample-size filter |

*(substituted)* = the originally-requested analysis wasn't supported by the
data; see the Dataset Availability Matrix and the file's own header comment
for exactly what replaced it and why. `04_cancellation_analysis.sql` keeps
its filename/number for consistency with this project's 01–10 scheme, but
internally is a **Profitability / Commercial-Risk Line Analysis** — it does
not measure, imply, or approximate cancellations.

---

## Exploratory Data Analysis

`notebooks/01_eda.ipynb` — executed top-to-bottom, all outputs saved. Covers
dataset overview, types, missing values, duplicates, data-quality validation,
distributions, univariate/bivariate/correlation analysis, time/seasonality,
location analysis, category analysis, and delivery-time analysis — each with
a business interpretation, not just a chart.

---

## KPI Definitions

Implemented in `src/metrics.py` (shared by the notebook and the dashboard so
the numbers can never drift between the two):

```
Total Orders             = distinct count of Order ID
Total Revenue            = Σ Sales
Average Order Value      = Total Revenue / Total Orders          (order grain)
Profit Margin %          = Σ Profit / Σ Sales × 100

Loss-Making Order Rate   = COUNT(orders where SUM(profit) < 0) / COUNT(distinct orders) × 100
                            (order grain — used for location/state bottleneck analysis,
                            since every order has exactly one ship-to state)

Loss-Making Line Rate    = COUNT(line items where profit < 0) / COUNT(line items) × 100
                            (line-item grain — used for discount-band and
                            state × sub-category analysis, since discount and
                            sub-category are line-item attributes, not order
                            attributes)

Neither of the above is a cancellation rate. This dataset has no
order_status field; both are documented proxies, applied at the grain
that's actually correct for each analysis rather than one being an
approximation of the other.

Avg Delivery Days             = MEAN(Ship Date − Order Date)     (day-level proxy)
Delivery Benchmark (per mode) = P75(Delivery Days) within that Ship Mode
                                 (an INTERNAL, DATA-DERIVED benchmark —
                                 NOT a contractual SLA; no promised-delivery
                                 field exists in this dataset)
% Over Benchmark               = COUNT(Delivery Days > that mode's P75) / COUNT(orders) × 100
Revenue / Profit by X          = Σ Sales / Σ Profit grouped by category, state, segment, etc.
```

KPIs **not** implemented (and why): Cancellation Rate, true On-Time Delivery
Rate, Orders per Hour — all require fields this dataset does not have (see
Dataset Availability Matrix). They were not approximated by inventing data.

---

## Operational Bottleneck Framework

**Methodology** (not an arbitrary score):

1. Compute two axes per segment:
   - **X = order volume** (how much this segment matters)
   - **Y = performance** — **order-level Loss-Making Order Rate** at the
     state grain (`sql/08_location_performance.sql`), or **line-level
     Loss-Making Line Rate** at the finer state × sub-category grain
     (`sql/10_operational_bottlenecks.sql`), because sub-category is a
     line-item attribute and an order can span several sub-categories —
     see KPI Definitions above for why these two are deliberately
     different metrics, not an inconsistency.
2. Compare each segment against the **overall median volume** and **overall
   average loss rate** (computed at the matching grain).
3. Classify into four quadrants:

| | Poor Performance | Good Performance |
|---|---|---|
| **High Volume** | 🔴 **PRIORITY** — investigate first | 🟢 **BENCHMARK** — study what's working |
| **Low Volume** | 🟡 **INVESTIGATE** — lower urgency, still worth a look | ⚪ **LOW PRIORITY** |

4. At the fine (state × sub-category) grain, segments with fewer than 5
   orders are excluded to avoid flagging statistical noise.

**Actual result (state level, order-level Loss-Making Order Rate):** Texas
(52.6% of 487 orders net loss-making), Pennsylvania (54.2% of 288 orders),
and Illinois (57.2% of 276 orders) all land in **High Volume / Poor
Performance**, against a **10.5%** average order-level loss rate across all
states (median volume ≈ 44 orders/state) — California and New York, by
contrast, combine similarly high volume (1,021 and 562 orders) with loss
rates of just 5.5% and 4.3% (**Benchmark** quadrant).

**Important nuance (checked, not assumed):** the state-level finding and
the discount-level finding below are **not two independent root causes** —
they are very likely the same underlying pattern observed at two different
grains. Average discount by state: Texas 37.0%, Illinois 39.0%,
Pennsylvania 32.9%, vs. California 7.3% and New York 5.5%. The states with
high loss rates are exactly the states with high average discounts. This
is called out explicitly so the two findings aren't mistakenly presented
as separate root causes in an interview — see Key Findings below for the
corrected wording.

---

## Dashboard

`app.py` — 4 pages: **Executive Overview**, **Operations**, **Product &
Revenue**, **Business Insights**. Filters (region, category, ship mode, date
range) apply across all pages. Every chart maps to one of the business
questions above; the Business Insights page renders Finding → Evidence →
Possible Cause → Recommended Action → KPI for each major finding, computed
live from whatever filters are active — nothing is hardcoded.

---

## Key Findings (actual, calculated numbers)

1. **18.7%** of order line items (1,871 of 9,994) are loss-making — the
   **Loss-Making Line Rate**. At the order level — summing profit across
   each order's own line items first — **20.4%** of the 5,009 distinct
   orders are net loss-making — the **Loss-Making Order Rate**. These are
   two different, correctly-labeled metrics at two different grains, not
   two measurements of the same thing (see KPI Definitions) — neither is a
   cancellation rate; this dataset has no `order_status` field.
2. **Discount depth is strongly associated with a higher Loss-Making LINE
   Rate** (FACT, correlational — not proven causal). Formula:
   `Loss-Making Line Rate = COUNT(line items with profit<0) / COUNT(line
   items)` per discount band. Sample sizes: 0% discount, n=4,798, 0.0%
   loss; 1–20%, n=3,803, 13.8% loss; 21–40%, n=460, 90.2% loss; **41%+,
   n=933, 100.0% loss**. All bands have sample sizes large enough to trust
   the direction of the pattern.
   **Caveat that changes how this should be framed:** the 41%+ band is not
   spread evenly across the business — 66% of it (613 of 933 line items) is
   a single sub-category, **Binders**, with the rest concentrated in 5 more
   sub-categories (Furnishings, Appliances, Tables, Machines, Bookcases).
   The 0%-discount band's exact 0.00% loss rate, and the exact 100.00% at
   41%+, are unusually clean for organic transaction data — consistent with
   this sample dataset's profit field being generated on a formula tied to
   discount and category rather than fully independent transactional noise.
   **Correct framing:** *"Heavy discounting (41%+) is associated with
   guaranteed line-item losses in this dataset, concentrated in a handful of
   already-thin-margin sub-categories — not a universal effect proven across
   the whole catalog."* Treat the causal direction (does discounting cause
   the loss, or are inherently low-margin items simply discounted more) as
   an open HYPOTHESIS, not a settled fact.
3. **Texas, Pennsylvania, and Illinois** are high-volume states with
   **order-level** Loss-Making Order Rates of 52.6% (487 orders), 54.2%
   (288 orders), and 57.2% (276 orders) respectively — roughly 5× the
   **10.5%** average across all states (median ≈44 orders/state) — while
   California (1,021 orders) and New York (562 orders) carry similarly high
   or higher volume at 5.5% and 4.3% loss rates. **This is very likely the
   same underlying pattern as Finding #2, not a second independent cause:**
   these same three states carry average discounts of 33–39%, vs. 5–7% in
   California and New York. The recommendation below reflects this — it
   targets discounting practice in those states, not the states themselves.
4. **Tables** (Furniture) has a **-8.6% profit margin** — the only
   sub-category in the bottom-6 by margin that's simultaneously a top-4
   sub-category by revenue ($206,966).
5. **Standard Class** shipments average **5.0 days**, more than double
   **Same Day** (0.05 days); **Second Class** has the highest share
   (21.0%) of its own orders exceeding its own internal, data-derived
   delivery benchmark — a self-referential comparison against that mode's
   own history, explicitly **not** a contractual SLA or a missed promise
   to a customer (this dataset has no promised-delivery-date field).
6. Demand **peaks in November–December**, consistent with holiday
   seasonality.

---

## Business Recommendations

| Action | Owner | KPI | Expected Direction |
|---|---|---|---|
| Cap discount approval at 30% without manager sign-off, starting with Binders and Tables (the two sub-categories driving most of the 41%+ discount volume); investigate why Texas/Pennsylvania/Illinois run 33–39% average discounts vs. 5–7% in California/New York as *one* discounting-policy question, not three separate state issues | Category / Pricing + Regional Ops (joint) | Loss-Making Order Rate (by state) and Loss-Making Line Rate (by discount band); Sub-Category Margin % | Should reduce the loss-rate concentration in deep-discount lines and narrow the state gap to the ~10.5% cross-state average |
| Investigate carrier/fulfillment consistency for Second Class shipments | Logistics / Carrier Management | % Orders Exceeding Ship-Mode Delivery Benchmark | Should reduce the 21% rate |
| Increase inventory/staffing readiness ahead of the Nov–Dec demand peak | Supply Chain / Ops Planning | Orders per Month vs. forecast | Should reduce peak-season strain |

Language throughout uses **"should be evaluated using..."** / **"could
potentially improve..."** — this dataset has no before/after intervention
data, so no claim is made that any of these actions *have* worked.

**FACT vs. HYPOTHESIS vs. RECOMMENDATION**, used consistently: a FACT is
something directly computed from the data (e.g. the 100% loss rate at 41%+
discount, or that Texas/Illinois/Pennsylvania average 33–39% discount vs.
5–7% in California/New York); a HYPOTHESIS is a plausible but unproven
explanation (e.g. *why* those states discount more heavily in the first
place — regional sales negotiation practice? a different customer mix? the
data doesn't say); a RECOMMENDATION is what to investigate or change next.

---

## Project Structure

```
quickops-analytics/
├── app.py
├── README.md
├── INTERVIEW_GUIDE.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/superstore_orders.csv
│   └── processed/orders_clean.csv
├── sql/
│   ├── schema.sql
│   └── 01_kpi_summary.sql … 10_operational_bottlenecks.sql
├── notebooks/
│   └── 01_eda.ipynb
├── src/
│   ├── data_cleaning.py
│   ├── data_loading.py
│   ├── metrics.py
│   └── utils.py
├── screenshots/
└── .streamlit/secrets.toml.example
```

---

## How to Run Locally

```bash
git clone <your-repo-url>
cd quickops-analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Clean the data
python src/data_cleaning.py

# 2. (Optional) Load into PostgreSQL for the SQL analysis layer
createdb quickops
export QUICKOPS_DB_PASSWORD=yourpassword   # QUICKOPS_DB_USER/HOST/NAME default to postgres/localhost/quickops
python src/data_loading.py
psql -d quickops -f sql/01_kpi_summary.sql   # run any of sql/01–10

# 3. Explore the notebook
jupyter notebook notebooks/01_eda.ipynb

# 4. Run the dashboard (reads the processed CSV directly — no DB required)
streamlit run app.py
```

## How to Deploy (Streamlit Community Cloud)

The dashboard needs **no database at runtime** — it reads
`data/processed/orders_clean.csv` directly, so the deployed app requires no
installs beyond `requirements.txt`.

1. Push this repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the repo, branch `main`, main file path `app.py`.
4. Click **Deploy**. No secrets are required for the default (CSV-backed) mode.

*(This app has not been deployed as part of producing this response — the
steps above are exact and sufficient to deploy it in a few minutes.)*

---

## Limitations

- No true order-status/cancellation field — Loss-Making Order Rate (order
  grain) and Loss-Making Line Rate (line-item grain) are both used as
  documented proxies, at the grain appropriate to each analysis; neither is
  a cancellation rate.
- No promised-delivery-date or timestamp field — delivery-time analysis is
  day-level only, and the delivery benchmark is a self-referential,
  internal, data-derived figure (75th percentile of each ship mode's own
  history) — explicitly **not** a contractual SLA or a promise-vs-actual
  comparison.
- No hour-of-day data — "peak hours" is answered at the month/day-of-week
  level instead.
- All causal explanations offered for findings are labeled HYPOTHESES, not
  proven causes — this dataset supports correlation, not causal inference.
- The discount→loss pattern is unusually clean (exact 0%→100% jumps),
  suggesting this sample dataset's profit field may be partly
  formula-generated rather than fully independent transactional noise — a
  real production dataset would likely be noisier, and the pattern should
  be re-validated there before acting on the exact numbers.
- Data covers 2014–2017 U.S. retail, not live quick-commerce operations —
  findings demonstrate analytical method, not current business performance.

## Future Improvements

- Real order-status/cancellation and minute-level delivery-timestamp data,
  if this method were applied to an actual quick-commerce operator.
- Automated daily refresh instead of a static CSV.
- Demand forecasting (a genuine ML use case, once descriptive/diagnostic
  analytics like this has been validated).
- Anomaly detection on daily KPI movement.
- A proper BI tool (Looker/Power BI) once the audience outgrows a single
  Streamlit app.
