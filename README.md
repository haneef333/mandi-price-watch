# Mandi Price Watch
### Are Maharashtra's farmers actually getting the government's Minimum Support Price?

🔗 **Live dashboard:** https://your-app-name.streamlit.app

A data analytics project that checks 20,707 real agricultural market transactions
against India's Minimum Support Price (MSP) policy, to find out where and when
Maharashtra's farmers are actually being paid below the government's price floor —
and what a state agriculture department or agri-procurement team should do about it.

---

## The business question

India's government sets a **Minimum Support Price (MSP)** each year for staple
crops — a guaranteed floor price meant to protect farmers from distress selling.
But MSP is only a policy on paper unless markets actually pay it. This project
asks three concrete questions:

1. What share of sales at Maharashtra's regulated markets (APMCs) happen **below**
   MSP, and what does that cost farmers?
2. **Where** and **when** is this worst — which districts, which markets, which
   months?
3. **Why** — is it driven by oversupply crashing prices, or something else, and
   what's the most defensible intervention?

## Headline findings

| Metric | Value |
|---|---|
| MSP-eligible transactions analyzed | 20,707 (2014–2016, 19 staple commodities, 349 markets) |
| Share sold below MSP | **26.8%** — roughly 1 in 4 |
| Estimated farmer shortfall | **₹210 crore** (conservative, see *Honesty check* below) |
| Trend | 34.5% (2014) → 34.1% (2015) → **18.0%** (2016) — improving, but still ~1 in 5 |
| Worst district | Buldhana — 52.0% of sales below MSP |
| Worst individual market | Roha (Raigad) — 91.7% of sales below MSP (small sample, 24 transactions) |
| Worst season | October–November, right after the kharif harvest |
| Biggest-loss crops | Maize (₹102.6 Cr), Sorghum/Jowar (₹46.3 Cr), Cotton (₹17.9 Cr) |

**The counter-intuitive finding:** low-volume markets (under 100 quintals arriving)
violate MSP **30.6%** of the time, versus **19.4%** for high-volume markets
(2,000+ quintals) — the opposite of the "harvest oversupply crashes the price"
story most people assume. This points to **thin markets with weak buyer
competition**, not harvest gluts, as the real driver — which changes where an
intervention should be targeted.

## Recommendation

Rather than a blanket statewide MSP enforcement push, the data supports a
**targeted intervention**: procurement support or price monitoring concentrated
in the worst-performing districts (Buldhana, Jalgaon, Akola, Nandurbar) during
October–November, with particular attention to **small, thin markets** rather
than large ones. The 15 markets that never once sold below MSP in this dataset
(e.g. Kolhapur-Laxmipuri, Lonand, Jamkhed) are a useful benchmark for what
functioning buyer competition looks like.

## Honesty check — the coconut flag

While building this, I found that COCONUT's average recorded arrival volume
(~98,090 quintals per transaction) is wildly out of line with every comparable
commodity — strongly suggesting a unit-recording inconsistency in the raw
government data rather than a real number. Rather than fold a possibly-wrong
₹104.6 crore into the headline total, **I excluded it and disclosed it
separately** (see `docs/data_quality_report.md` and the dashboard's Methodology
tab). The ₹210 Cr headline figure already excludes it. This is the kind of
judgment call I'd rather over-explain than hide — and it's genuinely one of the
more interesting decisions in this project.

## Data

- **Maharashtra APMC monthly commodity price bulletins** (CMO) — 62,429 records,
  349 markets, 352 raw commodity labels, 2014–2016. Government open data
  (data.gov.in / Maharashtra Cooperation, Marketing & Textiles department).
- **Government MSP schedule** — Minimum Support Price by commodity and year,
  2012–2016.

Both are real government datasets, not a synthetic or Kaggle-tutorial dataset.

## What I actually did (pipeline)

1. **`scripts/01_clean_data.py`** — cleaning & validation
   - Normalized commodity names: 352 raw labels → 202 true distinct commodities
     (pure case/whitespace duplicates, e.g. `Amla` / `AMLA` / `Amla `).
   - Flagged (not silently dropped) 296 rows with a logically impossible
     `min_price > max_price`, and 216 rows with a zero/negative price — 0.78%
     of records excluded from analysis, fully documented.
   - Merged in the MSP reference table, scoped to the 19 commodities MSP
     actually applies to (staples — MSP doesn't cover most fruit/veg).
   - Outputs a full data-quality report: `docs/data_quality_report.md`.

2. **`scripts/02_build_database.py`** — loads the cleaned data into a proper
   SQLite database (`mandi_analytics.db`) with a fact table + MSP dimension
   table and indexes, the way it would sit behind a BI tool in a real
   analytics stack.

3. **`sql/queries.sql`** — 8 business-question SQL queries: headline compliance
   rate, year-over-year trend, seasonality, worst districts/markets (window
   function ranking), commodity-level rupee impact, best-performing markets as
   a benchmark, and the arrival-volume-vs-compliance check.

4. **`scripts/03_eda_and_export.py`** — runs the analysis, sanity-checks the
   rupee estimates against unit-consistency issues, adds a supporting
   price-volatility analysis (coefficient of variation by commodity), and
   exports everything the dashboard needs.

5. **`app.py`** — an interactive Streamlit dashboard, deployed live on
   Streamlit Community Cloud. It reads directly from `mandi_analytics.db` and
   includes:
   - Filters for year, crop season, commodity, and district
   - Headline KPI tiles (transactions in view, % below MSP, average shortfall,
     estimated total farmer shortfall)
   - A time-trend chart of % of transactions below MSP
   - Ranked bar charts of the worst-hit commodities and districts
   - A searchable, filterable transaction-level data table

   A lightweight static HTML version (`dashboard/index.html`) is also kept in
   the repo as a dependency-free fallback view with the same core findings.

## Limitations (stated plainly, not buried)

- **Historical, not live**: 2014–2016 only, Maharashtra only. It shows where
  and when the problem concentrated in that window, not the current state.
- **Descriptive, not causal**: the "thin markets, not oversupply" reading comes
  from a correlation in the arrival-volume data, not a controlled test.
- **MSP coverage is partial by design**: only 19 of 202 commodities in the raw
  data carry an official MSP, so most fruits/vegetables are out of scope for
  the compliance analysis (though they appear in the volatility view).
- **One flagged unit inconsistency** (coconut) — excluded and disclosed, not
  hidden.

## Tech stack

Python (pandas) · SQLite + SQL (window functions, CTEs, aggregation) ·
Streamlit + Plotly (deployed dashboard) · static HTML/CSS/JS fallback view ·
designed to be rebuilt in Power BI or Tableau directly from
`data/processed/mandi_valid.csv` and `data/processed/mandi_msp_merged.csv` if a
desktop BI tool is preferred for an interview walkthrough.

## Repo structure

```
data/
  raw/                    original government CSVs, unmodified
  processed/              cleaned CSVs + SQLite database (gitignored except
                           the .db file, which is committed so the deployed
                           dashboard has data to read)
sql/
  queries.sql             8 commented business-question SQL queries
scripts/
  01_clean_data.py        cleaning & validation, writes data quality report
  02_build_database.py    builds the SQLite database
  03_eda_and_export.py    EDA, honesty checks, exports dashboard data
app.py                    Streamlit dashboard (deployed live)
requirements.txt          Python dependencies for the Streamlit app
dashboard/
  index.html              static fallback dashboard (no dependencies)
docs/
  data_quality_report.md  full before/after cleaning counts
  key_findings.json       machine-readable summary of every finding
```

## Running it yourself

```bash
# 1. Rebuild the data pipeline (optional — mandi_analytics.db is already committed)
pip install pandas
python scripts/01_clean_data.py
python scripts/02_build_database.py
python scripts/03_eda_and_export.py

# 2. Run the Streamlit dashboard
pip install -r requirements.txt
streamlit run app.py
```

Or just open `dashboard/index.html` directly in a browser for the static,
dependency-free view.