"""
Loads / refreshes the ticker universe from tickers.csv into the 'tickers' table.

Run this once when you set the project up, and again any time you edit tickers.csv
to add or remove a stock.

Usage:
    DATABASE_URL="postgresql://..." python seed_tickers.py
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(DB_URL)

df = pd.read_csv("tickers.csv")

with engine.begin() as conn:
    for _, row in df.iterrows():
        conn.execute(
            text("""
                INSERT INTO tickers (ticker, name)
                VALUES (:ticker, :name)
                ON CONFLICT (ticker) DO NOTHING
            """),
            {"ticker": row["ticker"], "name": None if pd.isna(row.get("name")) else row.get("name")},
        )

print(f"Seeded/verified {len(df)} tickers.")
