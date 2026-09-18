"""
utils.py
--------
Shared data-loading helper. The dashboard (app.py) reads the processed CSV
directly so the deployed app has zero external dependencies (no DB needed
on Streamlit Community Cloud). Local development can optionally point at
PostgreSQL instead - see load_from_postgres().
"""

import pandas as pd
from pathlib import Path

PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "orders_clean.csv"


def load_data(path: Path = PROCESSED_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["order_date", "ship_date"])
    return df


def load_from_postgres():
    """
    Optional: load the same data from PostgreSQL instead of the CSV.
    Requires the QUICKOPS_DB_* environment variables (see src/data_loading.py).
    Not used by the deployed Streamlit app - kept for local dev parity with
    the SQL analysis layer.
    """
    import os
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("QUICKOPS_DB_HOST", "localhost"),
        port=os.environ.get("QUICKOPS_DB_PORT", "5432"),
        dbname=os.environ.get("QUICKOPS_DB_NAME", "quickops"),
        user=os.environ.get("QUICKOPS_DB_USER", "postgres"),
        password=os.environ["QUICKOPS_DB_PASSWORD"],
    )
    df = pd.read_sql("SELECT * FROM vw_order_line_items", conn)
    conn.close()
    return df
