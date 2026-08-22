-- =====================================================================
-- Maharashtra Mandi Price Intelligence — Business Question SQL Queries
-- Database: data/processed/mandi_analytics.db
-- Table used for MSP-compliance analysis: mandi_msp
--   (valid, price-sanity-passed records, already joined to the MSP
--    reference table, restricted to the 19 commodities that actually
--    carry a government Minimum Support Price)
-- =====================================================================


-- ---------------------------------------------------------------------
-- Q1. Headline number: what share of MSP-eligible sales happened
--     BELOW the government's Minimum Support Price, and what did
--     that cost farmers in total, statewide?
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                                  AS total_transactions,
    SUM(is_below_msp)                                         AS transactions_below_msp,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)            AS pct_below_msp,
    ROUND(SUM(CASE WHEN is_below_msp = 1
              THEN (msp_price - modal_price) * arrivals_in_qtl
              ELSE 0 END), 0)                                 AS total_farmer_shortfall_rupees
FROM mandi_msp;


-- ---------------------------------------------------------------------
-- Q2. Is the problem getting better or worse over time?
--     Year-over-year MSP violation rate.
-- ---------------------------------------------------------------------
SELECT
    Year,
    COUNT(*)                                       AS transactions,
    SUM(is_below_msp)                              AS below_msp,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1) AS pct_below_msp
FROM mandi_msp
GROUP BY Year
ORDER BY Year;


-- ---------------------------------------------------------------------
-- Q3. Seasonality: which months of the year see the worst MSP
--     violation rates, aggregated across all three years?
--     (Useful for timing procurement / policy intervention.)
-- ---------------------------------------------------------------------
SELECT
    Month,
    COUNT(*)                                       AS transactions,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1) AS pct_below_msp
FROM mandi_msp
GROUP BY Month
ORDER BY pct_below_msp DESC;


-- ---------------------------------------------------------------------
-- Q4. Which districts fail farmers most often?
--     (min 50 transactions so tiny districts don't distort the ranking)
-- ---------------------------------------------------------------------
SELECT
    district_clean,
    COUNT(*)                                          AS transactions,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)     AS pct_below_msp,
    ROUND(AVG(CASE WHEN is_below_msp = 1
              THEN price_gap_pct_vs_msp END), 1)       AS avg_shortfall_pct_when_below
FROM mandi_msp
GROUP BY district_clean
HAVING COUNT(*) >= 50
ORDER BY pct_below_msp DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- Q5. Which individual APMC markets are the worst offenders?
--     Ranked with a window function; min 20 transactions to filter noise.
-- ---------------------------------------------------------------------
SELECT *
FROM (
    SELECT
        apmc_clean,
        district_clean,
        COUNT(*)                                       AS transactions,
        ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)  AS pct_below_msp,
        RANK() OVER (ORDER BY 1.0 * SUM(is_below_msp) / COUNT(*) DESC) AS worst_rank
    FROM mandi_msp
    GROUP BY apmc_clean, district_clean
    HAVING COUNT(*) >= 20
)
ORDER BY worst_rank
LIMIT 15;


-- ---------------------------------------------------------------------
-- Q6. Which commodities cost farmers the most in absolute rupee terms
--     when sold below MSP? (volume-weighted — a high violation % on a
--     low-volume crop matters less than a moderate % on a huge crop)
-- ---------------------------------------------------------------------
SELECT
    commodity_clean,
    COUNT(*)                                                   AS transactions,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)             AS pct_below_msp,
    ROUND(SUM(CASE WHEN is_below_msp = 1
              THEN (msp_price - modal_price) * arrivals_in_qtl
              ELSE 0 END), 0)                                  AS total_farmer_shortfall_rupees
FROM mandi_msp
GROUP BY commodity_clean
ORDER BY total_farmer_shortfall_rupees DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- Q7. Benchmark of good practice: which markets consistently pay AT
--     OR ABOVE MSP? (what "good" looks like, for a recommendation)
-- ---------------------------------------------------------------------
SELECT
    apmc_clean,
    district_clean,
    COUNT(*)                                       AS transactions,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)  AS pct_below_msp
FROM mandi_msp
GROUP BY apmc_clean, district_clean
HAVING COUNT(*) >= 20
ORDER BY pct_below_msp ASC
LIMIT 15;


-- ---------------------------------------------------------------------
-- Q8. Does higher arrival volume (more supply reaching the market)
--     correlate with a higher chance of the price falling below MSP?
--     (classic oversupply-depresses-price check)
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN arrivals_in_qtl < 100  THEN '1. under 100 qtl'
        WHEN arrivals_in_qtl < 500  THEN '2. 100-499 qtl'
        WHEN arrivals_in_qtl < 2000 THEN '3. 500-1999 qtl'
        ELSE '4. 2000+ qtl'
    END                                             AS arrival_volume_bucket,
    COUNT(*)                                        AS transactions,
    ROUND(100.0 * SUM(is_below_msp) / COUNT(*), 1)  AS pct_below_msp
FROM mandi_msp
GROUP BY arrival_volume_bucket
ORDER BY arrival_volume_bucket;
