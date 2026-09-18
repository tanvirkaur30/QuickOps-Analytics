"""
data_loading.py
----------------
Loads the cleaned QuickOps dataset into PostgreSQL following sql/schema.sql.

Credentials are read from environment variables - never hardcoded:
    QUICKOPS_DB_HOST     (default: localhost)
    QUICKOPS_DB_PORT     (default: 5432)
    QUICKOPS_DB_NAME     (default: quickops)
    QUICKOPS_DB_USER     (default: postgres)
    QUICKOPS_DB_PASSWORD (required, no default)

Run:
    python src/data_loading.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

CLEAN_PATH = Path("data/processed/orders_clean.csv")
SCHEMA_PATH = Path("sql/schema.sql")

REQUIRED_COLUMNS = [
    "row_id", "order_id", "order_date", "ship_date", "ship_mode",
    "customer_id", "customer_name", "segment", "country", "city", "state",
    "postal_code", "region", "product_id", "category", "sub_category",
    "product_name", "sales", "quantity", "discount", "profit",
    "delivery_days",
]


def get_connection():
    try:
        return psycopg2.connect(
            host=os.environ.get("QUICKOPS_DB_HOST", "localhost"),
            port=os.environ.get("QUICKOPS_DB_PORT", "5432"),
            dbname=os.environ.get("QUICKOPS_DB_NAME", "quickops"),
            user=os.environ.get("QUICKOPS_DB_USER", "postgres"),
            password=os.environ["QUICKOPS_DB_PASSWORD"],
        )
    except KeyError:
        sys.exit("ERROR: set QUICKOPS_DB_PASSWORD as an environment variable "
                 "before running this script.")
    except psycopg2.OperationalError as e:
        sys.exit(f"ERROR: could not connect to PostgreSQL: {e}")


def validate(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Cleaned dataset is missing expected columns: {missing}. "
                          f"Run src/data_cleaning.py first.")


def apply_schema(conn):
    with open(SCHEMA_PATH) as f:
        schema_sql = f.read()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()
    print("Schema applied.")


def load_data(conn, df: pd.DataFrame):
    with conn.cursor() as cur:
        # --- locations ---
        locations = df[["city", "state", "region", "country", "postal_code"]].drop_duplicates()
        execute_values(
            cur,
            """INSERT INTO locations (city, state, region, country, postal_code)
               VALUES %s ON CONFLICT DO NOTHING""",
            locations.values.tolist(),
        )

        cur.execute("SELECT location_id, city, state, postal_code FROM locations")
        loc_map = {(c, s, str(p)): lid for lid, c, s, p in cur.fetchall()}

        # --- customers ---
        customers = df[["customer_id", "customer_name", "segment"]].drop_duplicates()
        execute_values(
            cur,
            """INSERT INTO customers (customer_id, customer_name, segment)
               VALUES %s ON CONFLICT (customer_id) DO NOTHING""",
            customers.values.tolist(),
        )

        # --- products ---
        products = df[["product_id", "product_name", "category", "sub_category"]].drop_duplicates(subset="product_id")
        execute_values(
            cur,
            """INSERT INTO products (product_id, product_name, category, sub_category)
               VALUES %s ON CONFLICT (product_id) DO NOTHING""",
            products.values.tolist(),
        )

        # --- orders (order-level; one row per unique order_id) ---
        order_headers = df.drop_duplicates(subset="order_id").copy()
        order_rows = []
        for _, r in order_headers.iterrows():
            lid = loc_map[(r["city"], r["state"], str(r["postal_code"]))]
            order_rows.append((
                r["order_id"], r["customer_id"], lid,
                r["order_date"], r["ship_date"], r["ship_mode"], int(r["delivery_days"]),
            ))
        execute_values(
            cur,
            """INSERT INTO orders (order_id, customer_id, location_id, order_date,
                                    ship_date, ship_mode, delivery_days)
               VALUES %s ON CONFLICT (order_id) DO NOTHING""",
            order_rows,
        )

        # --- order_items (line-item grain) ---
        item_rows = df[["row_id", "order_id", "product_id", "sales", "quantity",
                         "discount", "profit"]].values.tolist()
        execute_values(
            cur,
            """INSERT INTO order_items (row_id, order_id, product_id, sales,
                                         quantity, discount, profit)
               VALUES %s ON CONFLICT (row_id) DO NOTHING""",
            item_rows,
        )
    conn.commit()
    print(f"Loaded {len(locations)} locations, {len(customers)} customers, "
          f"{len(products)} products, {len(order_headers)} orders, "
          f"{len(item_rows)} order line items.")


def main():
    print("Reading cleaned dataset...")
    df = pd.read_csv(CLEAN_PATH, parse_dates=["order_date", "ship_date"])
    validate(df)

    conn = get_connection()
    try:
        apply_schema(conn)
        load_data(conn, df)
    finally:
        conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
