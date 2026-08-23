import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mandi Price Watch — Maharashtra MSP Compliance",
    page_icon="🌾",
    layout="wide",
)

DB_PATH = Path(__file__).parent / "data" / "processed" / "mandi_analytics.db"


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    msp = pd.read_sql("SELECT * FROM mandi_msp", conn)
    prices = pd.read_sql("SELECT * FROM mandi_prices", conn)
    conn.close()

    msp["date"] = pd.to_datetime(msp["date"])
    prices["date"] = pd.to_datetime(prices["date"])
    return msp, prices


msp_df, prices_df = load_data()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🌾 Mandi Price Watch")
st.subheader("Are Maharashtra's farmers actually getting the government's Minimum Support Price?")

st.markdown(
    """
A data analytics project that checks **20,707 real agricultural market transactions**
against India's Minimum Support Price (MSP) policy, to find out where and when
Maharashtra's farmers are being paid **below** the government's price floor — and what
a state agriculture department or agri-procurement team should do about it.
"""
)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

years = sorted(msp_df["Year"].dropna().unique())
year_sel = st.sidebar.multiselect("Year", years, default=years)

seasons = sorted(msp_df["crop_season"].dropna().unique())
season_sel = st.sidebar.multiselect("Crop season", seasons, default=seasons)

commodities = sorted(msp_df["commodity_clean"].dropna().unique())
commodity_sel = st.sidebar.multiselect("Commodity", commodities, default=[])

districts = sorted(msp_df["district_clean"].dropna().unique())
district_sel = st.sidebar.multiselect("District", districts, default=[])

filtered = msp_df[
    msp_df["Year"].isin(year_sel) & msp_df["crop_season"].isin(season_sel)
]
if commodity_sel:
    filtered = filtered[filtered["commodity_clean"].isin(commodity_sel)]
if district_sel:
    filtered = filtered[filtered["district_clean"].isin(district_sel)]

if filtered.empty:
    st.warning("No transactions match the current filters. Try widening your selection.")
    st.stop()

# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------
total_txn = len(filtered)
below_msp = filtered["is_below_msp"].sum()
pct_below = below_msp / total_txn * 100

shortfall_all = filtered.loc[filtered["is_below_msp"] == 1, "price_gap_vs_msp"].abs()
shortfall_qty = (
    filtered.loc[filtered["is_below_msp"] == 1, "price_gap_vs_msp"].abs()
    * filtered.loc[filtered["is_below_msp"] == 1, "arrivals_in_qtl"]
).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions in view", f"{total_txn:,}")
col2.metric("Below MSP", f"{below_msp:,}", f"{pct_below:.1f}%")
col3.metric("Avg. shortfall (below-MSP rows)", f"₹{shortfall_all.mean():,.0f}/qtl" if len(shortfall_all) else "—")
col4.metric("Estimated farmer shortfall", f"₹{shortfall_qty:,.0f}")

st.caption(
    "Estimated farmer shortfall = (MSP − modal price) × arrivals in quintals, summed across all "
    "below-MSP transactions currently in view. Treat this as an order-of-magnitude estimate, not an audit figure."
)

st.divider()

# ---------------------------------------------------------------------------
# Trend over time
# ---------------------------------------------------------------------------
st.markdown("### Share of transactions below MSP, over time")

trend = (
    filtered.groupby(["Year", "Month"])
    .agg(pct_below=("is_below_msp", "mean"), n=("is_below_msp", "size"))
    .reset_index()
)
trend["pct_below"] = trend["pct_below"] * 100
trend["period"] = trend["Year"].astype(str) + "-" + trend["Month"].astype(str)

fig_trend = px.line(
    trend.sort_values(["Year"]),
    x="period",
    y="pct_below",
    markers=True,
    labels={"pct_below": "% below MSP", "period": "Period"},
)
fig_trend.update_layout(height=380)
st.plotly_chart(fig_trend, use_container_width=True)

# ---------------------------------------------------------------------------
# By commodity
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.markdown("### Worst-hit commodities")
    by_commodity = (
        filtered.groupby("commodity_clean")
        .agg(
            transactions=("is_below_msp", "size"),
            pct_below=("is_below_msp", "mean"),
        )
        .reset_index()
    )
    by_commodity["pct_below"] = by_commodity["pct_below"] * 100
    by_commodity = by_commodity[by_commodity["transactions"] >= 20].sort_values(
        "pct_below", ascending=False
    ).head(10)

    fig_commodity = px.bar(
        by_commodity,
        x="pct_below",
        y="commodity_clean",
        orientation="h",
        labels={"pct_below": "% below MSP", "commodity_clean": "Commodity"},
    )
    fig_commodity.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_commodity, use_container_width=True)

with right:
    st.markdown("### Worst-hit districts")
    by_district = (
        filtered.groupby("district_clean")
        .agg(
            transactions=("is_below_msp", "size"),
            pct_below=("is_below_msp", "mean"),
        )
        .reset_index()
    )
    by_district["pct_below"] = by_district["pct_below"] * 100
    by_district = by_district[by_district["transactions"] >= 20].sort_values(
        "pct_below", ascending=False
    ).head(10)

    fig_district = px.bar(
        by_district,
        x="pct_below",
        y="district_clean",
        orientation="h",
        labels={"pct_below": "% below MSP", "district_clean": "District"},
    )
    fig_district.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_district, use_container_width=True)

st.caption("Only commodities/districts with at least 20 transactions in the current view are shown, to avoid noisy small-sample rankings.")

st.divider()

# ---------------------------------------------------------------------------
# Raw data explorer
# ---------------------------------------------------------------------------
st.markdown("### Explore the transactions")

show_only_below = st.checkbox("Show only below-MSP transactions", value=False)
table = filtered.copy()
if show_only_below:
    table = table[table["is_below_msp"] == 1]

st.dataframe(
    table[
        [
            "date",
            "district_clean",
            "apmc_clean",
            "commodity_clean",
            "modal_price",
            "msp_price",
            "price_gap_vs_msp",
            "price_gap_pct_vs_msp",
            "is_below_msp",
        ]
    ].sort_values("date", ascending=False),
    use_container_width=True,
    height=350,
)

st.caption(
    "Source: Maharashtra APMC monthly mandi price data (CMO), matched against official MSP tables. "
    "Built by Mohammed Haneef — [github.com/haneef333/mandi-price-watch](https://github.com/haneef333/mandi-price-watch)"
)
