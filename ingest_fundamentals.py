"""
Weekly ingestion job: balance sheet, income statement, cashflow, and company info.

These change quarterly at most, so running this weekly (instead of daily) is plenty,
and keeps well clear of Yahoo Finance rate limits.

Usage:
    DATABASE_URL="postgresql://..." python ingest_fundamentals.py
"""
import os
import json
import time

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(DB_URL)
SLEEP_BETWEEN_TICKERS = 1.5

# yfinance attribute -> (statement name, period type) stored in the 'financials' table
STATEMENTS = {
    "balance_sheet": ("balance_sheet", "annual"),
    "quarterly_balance_sheet": ("balance_sheet", "quarterly"),
    "financials": ("income_statement", "annual"),
    "quarterly_financials": ("income_statement", "quarterly"),
    "cashflow": ("cashflow", "annual"),
    "quarterly_cashflow": ("cashflow", "quarterly"),
}


def get_active_tickers():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT ticker FROM tickers WHERE active = TRUE ORDER BY ticker")).fetchall()
    return [r[0] for r in rows]


def upsert_financials(df, ticker, statement, period_type):
    if df is None or df.empty:
        return
    long_df = df.reset_index().melt(id_vars=df.reset_index().columns[0], var_name="fiscal_date", value_name="value")
    long_df.columns = ["line_item", "fiscal_date", "value"]
    long_df = long_df.dropna(subset=["value"])
    long_df["ticker"] = ticker
    long_df["statement"] = statement
    long_df["period_type"] = period_type
    long_df["fiscal_date"] = pd.to_datetime(long_df["fiscal_date"], errors="coerce").dt.date
    long_df = long_df.dropna(subset=["fiscal_date"])
    records = long_df.to_dict("records")
    if not records:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO financials (ticker, statement, period_type, fiscal_date, line_item, value)
            VALUES (:ticker, :statement, :period_type, :fiscal_date, :line_item, :value)
            ON CONFLICT (ticker, statement, period_type, fiscal_date, line_item)
            DO UPDATE SET value = EXCLUDED.value, fetched_at = now()
        """), records)


def upsert_info(ticker, info):
    if not info:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO company_info (ticker, info, updated_at) VALUES (:ticker, :info, now())
            ON CONFLICT (ticker) DO UPDATE SET info = EXCLUDED.info, updated_at = now()
        """), {"ticker": ticker, "info": json.dumps(info, default=str)})


def log(job, ticker, status, message=""):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ingestion_log (job_name, ticker, status, message)
            VALUES (:job, :ticker, :status, :message)
        """), {"job": job, "ticker": ticker, "status": status, "message": (message or "")[:500]})


def main():
    tickers = get_active_tickers()
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            for attr, (statement, period_type) in STATEMENTS.items():
                df = getattr(tk, attr, None)
                upsert_financials(df, t, statement, period_type)
            upsert_info(t, tk.info)
            log("ingest_fundamentals", t, "ok")
        except Exception as e:
            log("ingest_fundamentals", t, "error", str(e))
        time.sleep(SLEEP_BETWEEN_TICKERS)
    print("Done.")


if __name__ == "__main__":
    main()
