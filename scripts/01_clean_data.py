"""
01_clean_data.py
-----------------
Cleans the raw Maharashtra APMC (mandi) monthly commodity price data and
merges it with the government's Minimum Support Price (MSP) reference table.

Source data:
    data/raw/Monthly_data_cmo.csv   - 62,429 monthly APMC price records (2014-2016)
    data/raw/CMO_MSP_Mandi.csv      - Minimum Support Price by commodity/year (2012-2016)

Why this cleaning is needed (real issues found in the raw data):
    1. Commodity names are inconsistently cased/spaced -> 352 raw labels collapse
       to 202 true distinct commodities once normalized.
    2. 296 records have min_price > max_price, which is logically impossible for
       a market price range. Kept aside as invalid, not silently dropped.
    3. 216 records have a zero or negative price, which cannot be a real price.
    4. 748 records have a modal_price that falls outside the [min_price, max_price]
       band reported for that same row - a softer data-quality flag, kept but marked.
    5. MSP only exists for ~19 of the 202 commodities (staple/policy crops such as
       wheat, bajri, maize, cotton, tur, etc.) - MSP does not apply to most fruit
       and vegetable commodities, so the MSP-compliance analysis is intentionally
       scoped to only the commodities the government actually sets an MSP for.

Outputs:
    data/processed/mandi_clean.csv        - all rows, with data-quality flags added
    data/processed/mandi_valid.csv        - only rows that passed price-sanity checks
    data/processed/mandi_msp_merged.csv   - valid rows joined to MSP for MSP-eligible
                                             commodity/year combinations
    docs/data_quality_report.md           - before/after summary of every cleaning step
"""

import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

report_lines = []
def log(line=""):
    print(line)
    report_lines.append(line)


def main():
    log("# Data Quality Report — Maharashtra APMC Mandi Price Data\n")

    # ---------------------------------------------------------------
    # 1. Load raw data
    # ---------------------------------------------------------------
    df = pd.read_csv(RAW_DIR / "Monthly_data_cmo.csv")
    msp = pd.read_csv(RAW_DIR / "CMO_MSP_Mandi.csv")
    log(f"Raw monthly price records loaded: {len(df):,}")
    log(f"Raw MSP reference records loaded: {len(msp):,}\n")

    # ---------------------------------------------------------------
    # 2. Normalize text fields (case / whitespace inconsistencies)
    # ---------------------------------------------------------------
    raw_commodity_count = df["Commodity"].nunique()
    df["commodity_clean"] = df["Commodity"].str.strip().str.upper()
    df["apmc_clean"] = df["APMC"].str.strip().str.title()
    df["district_clean"] = df["district_name"].str.strip().str.title()
    clean_commodity_count = df["commodity_clean"].nunique()
    log("## 1. Commodity name normalization")
    log(f"- Distinct commodity labels before normalizing case/whitespace: {raw_commodity_count}")
    log(f"- Distinct commodity labels after normalizing (upper + strip):  {clean_commodity_count}")
    log(f"- {raw_commodity_count - clean_commodity_count} labels were pure formatting duplicates "
        f"(e.g. 'Amla' / 'AMLA' / 'Amla ' all collapse to one commodity).\n")

    # ---------------------------------------------------------------
    # 3. Parse the arrival date to a real date type
    # ---------------------------------------------------------------
    df["arrival_month"] = pd.to_datetime(df["date"], format="%Y-%m")

    # ---------------------------------------------------------------
    # 4. Flag price-sanity issues (do NOT silently drop — flag + report)
    # ---------------------------------------------------------------
    df["flag_min_gt_max"] = df["min_price"] > df["max_price"]
    df["flag_non_positive_price"] = (df[["min_price", "max_price", "modal_price"]] <= 0).any(axis=1)
    df["flag_modal_out_of_range"] = (
        (df["modal_price"] < df["min_price"]) | (df["modal_price"] > df["max_price"])
    ) & ~df["flag_min_gt_max"]

    n_min_gt_max = df["flag_min_gt_max"].sum()
    n_non_positive = df["flag_non_positive_price"].sum()
    n_modal_oor = df["flag_modal_out_of_range"].sum()

    log("## 2. Price-sanity checks")
    log(f"- Rows where min_price > max_price (impossible range): {n_min_gt_max}")
    log(f"- Rows with a zero or negative price:                  {n_non_positive}")
    log(f"- Rows where modal_price falls outside [min, max]:     {n_modal_oor}")

    df["is_valid_price"] = ~(df["flag_min_gt_max"] | df["flag_non_positive_price"])
    n_invalid = (~df["is_valid_price"]).sum()
    log(f"- Total rows excluded from price-based analysis:       {n_invalid} "
        f"({n_invalid/len(df):.2%} of all records)\n")

    # ---------------------------------------------------------------
    # 5. Save the full flagged dataset + the valid-only dataset
    # ---------------------------------------------------------------
    df.to_csv(PROCESSED_DIR / "mandi_clean.csv", index=False)
    valid = df[df["is_valid_price"]].copy()
    valid.to_csv(PROCESSED_DIR / "mandi_valid.csv", index=False)
    log(f"Saved: data/processed/mandi_clean.csv  ({len(df):,} rows, all rows + flags)")
    log(f"Saved: data/processed/mandi_valid.csv  ({len(valid):,} rows, price-sanity passed)\n")

    # ---------------------------------------------------------------
    # 6. Merge with MSP reference data (scoped to MSP-eligible commodities)
    # ---------------------------------------------------------------
    msp["commodity_clean"] = msp["commodity"].str.strip().str.upper()
    msp_small = msp[["commodity_clean", "year", "Type", "msprice"]].rename(
        columns={"year": "Year", "Type": "crop_season", "msprice": "msp_price"}
    )

    overlap_commodities = sorted(
        set(valid["commodity_clean"]) & set(msp_small["commodity_clean"])
    )
    merged = valid.merge(msp_small, on=["commodity_clean", "Year"], how="inner")

    log("## 3. MSP (Minimum Support Price) merge")
    log(f"- Commodities covered by an official MSP, present in this data: {len(overlap_commodities)}")
    log(f"  {overlap_commodities}")
    log(f"- MSP applies to national staple/policy crops only (cereals, pulses, oilseeds, "
        f"cotton, sugarcane) — not to most fruits and vegetables, so this is expected, "
        f"not a data problem.")
    log(f"- Rows in the MSP-eligible subset used for the compliance analysis: {len(merged):,}\n")

    merged["is_below_msp"] = merged["modal_price"] < merged["msp_price"]
    merged["price_gap_vs_msp"] = merged["modal_price"] - merged["msp_price"]
    merged["price_gap_pct_vs_msp"] = (merged["price_gap_vs_msp"] / merged["msp_price"]) * 100

    merged.to_csv(PROCESSED_DIR / "mandi_msp_merged.csv", index=False)
    log(f"Saved: data/processed/mandi_msp_merged.csv ({len(merged):,} rows)\n")

    below = merged["is_below_msp"].mean()
    log("## 4. Headline finding")
    log(f"- Across all MSP-eligible transactions, {below:.1%} were recorded at a modal "
        f"market price BELOW the government's Minimum Support Price for that commodity/year.")

    # ---------------------------------------------------------------
    # 7. Write the report to disk
    # ---------------------------------------------------------------
    (DOCS_DIR / "data_quality_report.md").write_text("\n".join(report_lines))
    print("\nWrote docs/data_quality_report.md")


if __name__ == "__main__":
    main()
