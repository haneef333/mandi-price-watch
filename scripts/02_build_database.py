"""
02_build_database.py
---------------------
Loads the cleaned data into a proper relational SQLite database
(mandi_analytics.db) so the project can be queried with real SQL,
the way it would sit behind a BI tool in a real analytics team.

Tables:
    mandi_prices   - every valid monthly APMC price record (fact table)
    msp_reference  - government Minimum Support Price by commodity/year (dimension)
    mandi_msp      - the pre-joined MSP-eligible subset used for the compliance analysis
"""

import sqlite3
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROCESSED = BASE / "data" / "processed"
DB_PATH = BASE / "data" / "processed" / "mandi_analytics.db"

def main():
    valid = pd.read_csv(PROCESSED / "mandi_valid.csv")
    msp_merged = pd.read_csv(PROCESSED / "mandi_msp_merged.csv")
    raw_msp = pd.read_csv(BASE / "data" / "raw" / "CMO_MSP_Mandi.csv")

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)

    valid.to_sql("mandi_prices", conn, index=False)
    raw_msp.to_sql("msp_reference", conn, index=False)
    msp_merged.to_sql("mandi_msp", conn, index=False)

    # Helpful indexes for the query patterns we'll run
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_mandi_prices_commodity ON mandi_prices(commodity_clean)")
    cur.execute("CREATE INDEX idx_mandi_prices_district ON mandi_prices(district_clean)")
    cur.execute("CREATE INDEX idx_mandi_prices_year ON mandi_prices(Year)")
    cur.execute("CREATE INDEX idx_mandi_msp_commodity ON mandi_msp(commodity_clean)")
    cur.execute("CREATE INDEX idx_mandi_msp_district ON mandi_msp(district_clean)")
    conn.commit()

    for t in ["mandi_prices", "msp_reference", "mandi_msp"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n:,} rows")

    conn.close()
    print(f"\nDatabase written to {DB_PATH}")

if __name__ == "__main__":
    main()
