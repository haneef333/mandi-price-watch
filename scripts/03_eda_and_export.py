"""
03_eda_and_export.py
---------------------
Runs the business-question SQL queries (sql/queries.sql), adds a
supporting price-volatility analysis in pandas, sanity-checks the
"total rupee shortfall" numbers against unit-consistency issues in the
raw arrivals_in_qtl field, and exports everything the dashboard needs
as compact JSON (dashboard/data.json) plus a written stats summary
(docs/key_findings.json) that the README and interview-prep docs pull from.
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "processed" / "mandi_analytics.db"
DASHBOARD_DIR = BASE / "dashboard"
DOCS_DIR = BASE / "docs"
DASHBOARD_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)


def q(sql):
    return pd.read_sql_query(sql, conn)


def main():
    out = {}

    headline = q("""
        SELECT COUNT(*) AS total_transactions,
               SUM(is_below_msp) AS transactions_below_msp,
               ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp,
               ROUND(SUM(CASE WHEN is_below_msp=1 THEN (msp_price-modal_price)*arrivals_in_qtl ELSE 0 END),0) AS total_farmer_shortfall_rupees
        FROM mandi_msp
    """).iloc[0].to_dict()

    # Honesty check: COCONUT's mean arrivals_in_qtl (~98,000 quintals per
    # transaction) is far above every other MSP-eligible commodity and is not
    # documented anywhere in the source data as a genuine unit. Rather than
    # silently including a possibly unit-mismatched figure in the headline
    # rupee number, we report the total both ways.
    coconut_shortfall = q("""
        SELECT ROUND(SUM(CASE WHEN is_below_msp=1 THEN (msp_price-modal_price)*arrivals_in_qtl ELSE 0 END),0) AS v
        FROM mandi_msp WHERE commodity_clean = 'COCONUT'
    """).iloc[0]["v"]
    headline["total_farmer_shortfall_rupees_excl_coconut"] = headline["total_farmer_shortfall_rupees"] - coconut_shortfall
    headline["coconut_shortfall_rupees_flagged"] = coconut_shortfall
    out["headline"] = headline

    out["by_year"] = q("""
        SELECT Year, COUNT(*) AS transactions, ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY Year ORDER BY Year
    """).to_dict(orient="records")

    out["by_month"] = q("""
        SELECT Month, COUNT(*) AS transactions, ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY Month ORDER BY pct_below_msp DESC
    """).to_dict(orient="records")

    out["worst_districts"] = q("""
        SELECT district_clean AS district, COUNT(*) AS transactions,
               ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY district_clean HAVING COUNT(*)>=50
        ORDER BY pct_below_msp DESC LIMIT 15
    """).to_dict(orient="records")

    out["worst_apmcs"] = q("""
        SELECT apmc_clean AS apmc, district_clean AS district, COUNT(*) AS transactions,
               ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY apmc_clean, district_clean HAVING COUNT(*)>=20
        ORDER BY pct_below_msp DESC LIMIT 15
    """).to_dict(orient="records")

    out["best_apmcs"] = q("""
        SELECT apmc_clean AS apmc, district_clean AS district, COUNT(*) AS transactions,
               ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY apmc_clean, district_clean HAVING COUNT(*)>=20
        ORDER BY pct_below_msp ASC LIMIT 15
    """).to_dict(orient="records")

    out["by_commodity"] = q("""
        SELECT commodity_clean AS commodity, COUNT(*) AS transactions,
               ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp,
               ROUND(SUM(CASE WHEN is_below_msp=1 THEN (msp_price-modal_price)*arrivals_in_qtl ELSE 0 END),0) AS total_farmer_shortfall_rupees
        FROM mandi_msp GROUP BY commodity_clean ORDER BY total_farmer_shortfall_rupees DESC
    """).to_dict(orient="records")

    out["by_arrival_bucket"] = q("""
        SELECT CASE WHEN arrivals_in_qtl<100 THEN '<100 qtl'
                    WHEN arrivals_in_qtl<500 THEN '100-499 qtl'
                    WHEN arrivals_in_qtl<2000 THEN '500-1999 qtl'
                    ELSE '2000+ qtl' END AS bucket,
               COUNT(*) AS transactions, ROUND(100.0*SUM(is_below_msp)/COUNT(*),1) AS pct_below_msp
        FROM mandi_msp GROUP BY bucket
    """).to_dict(orient="records")

    # -----------------------------------------------------------------
    # Sanity check: is the rupee-shortfall figure trustworthy, or is it
    # being driven by a handful of commodities with implausibly high
    # arrivals_in_qtl (a likely unit-recording inconsistency in the raw
    # government data)?
    # -----------------------------------------------------------------
    valid = pd.read_csv(BASE / "data" / "processed" / "mandi_valid.csv")
    arrival_stats = (valid.groupby("commodity_clean")["arrivals_in_qtl"]
                      .agg(["count", "mean", "median", "max"])
                      .sort_values("mean", ascending=False))
    out["arrival_unit_check_top10"] = (arrival_stats.head(10)
                                        .reset_index()
                                        .round(0)
                                        .to_dict(orient="records"))

    # -----------------------------------------------------------------
    # Supporting analysis: price volatility per commodity (coefficient
    # of variation of modal_price), on the full valid dataset, restricted
    # to commodities with a reasonable sample size. This is *not* part of
    # the MSP-compliance headline — it's supporting context for the
    # "which markets are riskiest for farmers/traders" angle.
    # -----------------------------------------------------------------
    vol = (valid[valid["commodity_clean"].map(valid["commodity_clean"].value_counts()) >= 100]
           .groupby("commodity_clean")["modal_price"]
           .agg(["mean", "std", "count"]))
    vol["coefficient_of_variation_pct"] = (vol["std"] / vol["mean"] * 100).round(1)
    vol = vol.sort_values("coefficient_of_variation_pct", ascending=False).head(15)
    out["most_volatile_commodities"] = (vol.reset_index()
                                         .round(1)
                                         .rename(columns={"commodity_clean": "commodity"})
                                         [["commodity", "mean", "coefficient_of_variation_pct", "count"]]
                                         .to_dict(orient="records"))

    # -----------------------------------------------------------------
    # Write outputs
    # -----------------------------------------------------------------
    with open(DASHBOARD_DIR / "data.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    with open(DOCS_DIR / "key_findings.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("Headline:", headline)
    print("\nArrival-volume unit sanity check (top 10 commodities by mean arrivals_in_qtl):")
    print(arrival_stats.head(10))
    print("\nMost volatile commodities (by coefficient of variation of modal price):")
    print(vol.head(10))
    print(f"\nWrote {DASHBOARD_DIR / 'data.json'}")
    print(f"Wrote {DOCS_DIR / 'key_findings.json'}")


if __name__ == "__main__":
    main()
