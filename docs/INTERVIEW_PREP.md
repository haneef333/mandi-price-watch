# Interview Prep — Mandi Price Watch

Grounded in what was actually built. Numbers here match the README and
dashboard exactly — if an interviewer pushes on a number, you can defend it.

---

## 1. "Walk me through this project in 60 seconds."

"I analyzed 62,000 real government records of agricultural market prices
across Maharashtra — 349 markets, three years — to check whether farmers were
actually getting the government's Minimum Support Price. After cleaning the
data in Python and loading it into SQLite, I found that about 27% of eligible
sales happened below MSP, costing farmers an estimated ₹210 crore over the
period. I built an interactive dashboard that breaks that down by district,
market, commodity, and season, and found the violation is concentrated in a
handful of districts right after harvest — and, counter-intuitively, worse in
small thin markets than in big ones. I'd recommend targeted procurement
support there rather than a blanket policy."

## 2. "Why this dataset? Why not something more standard?"

Be honest: you specifically avoided Titanic/Superstore/DataCo because every
fresher's portfolio has one of those, and you wanted something you could
defend with real domain understanding. This is real government data with real
messiness, and it maps to an actual business function (agri-market
intelligence / procurement) that Indian agri-tech and commodity-trading
companies hire analysts for.

## 3. "What was the hardest part of the data cleaning?"

Two concrete things, with numbers:
- 352 raw commodity labels collapsed to 202 once you normalized case and
  whitespace — a pure formatting problem, but if you don't catch it you
  silently undercount how many transactions exist for a given crop.
- 296 rows had `min_price > max_price`, which is logically impossible. You
  didn't just drop them — you flagged them, counted them, and reported the
  percentage excluded (0.78%), because a hiring manager wants to see you
  *show* the cleaning, not hide it.

## 4. "Tell me about a mistake or something you almost got wrong."

This is your strongest answer — lead with it if asked about limitations or
mistakes. Coconut's average arrival volume was ~98,000 quintals per
transaction — wildly higher than every comparable commodity. If you'd left it
in, your headline "farmer shortfall" number would have been overstated by
about a third (₹104.6 Cr on top of ₹210 Cr). Instead of trusting the SQL
output blindly, you profiled the arrivals column, noticed the anomaly, and
made the judgment call to exclude and disclose it rather than report an
inflated number. That's the difference between running queries and doing
analysis.

## 5. "Why SQL and not just pandas for everything?"

Because a real analytics stack usually has data living in a database, and
being able to write a ranking query with a window function (`RANK() OVER
(ORDER BY ...)`) or a `GROUP BY ... HAVING` filter is a distinct, testable
skill from pandas manipulation. You used both deliberately: SQL for the
business-question queries (the kind a stakeholder would actually ask), pandas
for statistical work SQL isn't suited for (coefficient of variation, the
arrival-unit sanity check).

## 6. "Explain one SQL query in detail."

Good pick — Q5, the worst-markets ranking:
```sql
SELECT *
FROM (
    SELECT apmc_clean, district_clean,
           COUNT(*) AS transactions,
           ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1) AS pct_below_msp,
           RANK() OVER (ORDER BY 1.0 * SUM(is_below_msp) / COUNT(*) DESC) AS worst_rank
    FROM mandi_msp
    GROUP BY apmc_clean, district_clean
    HAVING COUNT(*) >= 20
)
ORDER BY worst_rank
LIMIT 15;
```
Explain: `GROUP BY` two columns because the same market name can theoretically
repeat across districts; `HAVING COUNT(*) >= 20` filters out markets with too
few transactions to trust a percentage from (a market with 3 transactions and
2 violations would show 67% and dominate the ranking without this); the
window function `RANK()` is computed inside a subquery so you can order by the
rank column cleanly outside it.

## 7. "Is this correlation or causation? How do you know oversupply doesn't
cause it?"

You don't know for certain — say so. What you found is that low-volume
markets have a *higher* violation rate than high-volume ones, which is the
opposite of what the "harvest floods the market" theory would predict. That's
a real, defensible pattern in the data, but it's descriptive — you'd want a
market-structure variable (number of buyers/licensed traders per APMC) to
actually test the "thin market, weak competition" hypothesis causally. Name
this as the natural next step if asked "what would you do with more time/data".

## 8. "How would you turn this into a live dashboard a company could actually
use?"

The pipeline (`01_clean_data.py` → `02_build_database.py` →
`03_eda_and_export.py`) is already structured so a scheduler (cron / Airflow)
could re-run it monthly against a fresh government data pull, and the
dashboard's data layer is a single JSON export — swapping that for a live
database connection (or rebuilding the same views in Power BI/Tableau
pointed at the SQLite/Postgres database) is a mechanical next step, not a
redesign.

## 9. "What would you do differently with more time?"

Be honest and specific, not vague:
- Bring in a second year of MSP data beyond 2016 if available, to see if the
  improving trend continued.
- Get a market-structure dataset (number of licensed traders per APMC) to
  actually test the thin-market hypothesis instead of inferring it.
- Extend beyond Maharashtra if comparable state-level data exists, to see if
  the pattern generalizes.

## 10. "What's your process when you don't trust a number?"

Use the coconut example as your concrete process: (1) look at the distribution
of the underlying field, not just the aggregate; (2) compare the suspicious
value against comparable categories; (3) decide whether to exclude, adjust, or
flag — and always disclose the decision rather than silently picking whichever
number looks better.

## 11. Numbers to have cold

- 62,429 raw records → 61,944 valid (99.22%) → 20,707 MSP-eligible
- 349 markets, 202 distinct commodities, 19 MSP-eligible commodities
- 26.8% below MSP overall; 34.5% (2014) → 18.0% (2016)
- ₹210 Cr estimated shortfall (excl. flagged coconut ₹104.6 Cr)
- Worst district: Buldhana, 52.0%; best markets: 0% (e.g. Kolhapur-Laxmipuri,
  165 transactions, zero violations)
- Low-volume markets 30.6% violation vs high-volume 19.4%
