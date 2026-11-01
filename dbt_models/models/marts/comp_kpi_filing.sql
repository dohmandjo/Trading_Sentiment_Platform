-- One row per 10-K filing that can be compared with the company's previous filing.
--
-- Row selection (intentional, see the yml description):
--   * risk_cosine_distance IS NOT NULL  -> the filing has a previous filing to compare with, so each
--     company's first filing is excluded
--   * valid_filing_count > 1            -> companies with at least two such filings, so every company has a trend
--
-- Sentiment inputs
--   * Loughran-McDonald shares: average of BUSINESS and MDA sections (managerial voice)
--   * FinBERT score: BUSINESS + MDA average (management) and RISKS separately (disclosure tone)

WITH base AS (
    SELECT
        cik,
        company_name,
        tickers,
        filing_date,
        accessionNumber,
        form_type,
        market_cap,
        sector
    FROM {{ ref('stg_cleaned_filings') }}
    WHERE form_type = '10-K'
),

lm_managerial_agg AS (
    SELECT
        cik,
        filing_date,
        AVG(optimism_per_1k) AS optimism_per_1k_avg,
        AVG(caution_per_1k)  AS caution_per_1k_avg,
        AVG(concern_per_1k)  AS concern_per_1k_avg,
        AVG(optimism_share)  AS optimism_share_avg,
        AVG(caution_share)   AS caution_share_avg,
        AVG(concern_share)   AS concern_share_avg
    FROM {{ source('sec_filings', 'fact_lm_sentiment') }}
    WHERE section_name IN ('BUSINESS', 'MDA')
    GROUP BY cik, filing_date
),

finbert AS (
    SELECT
        cik,
        filing_date,
        AVG(CASE WHEN section_name IN ('BUSINESS', 'MDA') THEN sentiment_score END) AS finbert_mgmt_score,
        AVG(CASE WHEN section_name = 'RISKS' THEN sentiment_score END)              AS finbert_risk_score,
        AVG(CASE WHEN section_name = 'RISKS' THEN negative_prob END)                AS finbert_risk_negative_prob
    FROM {{ source('sec_filings', 'fact_finbert_sentiment') }}
    GROUP BY cik, filing_date
),

risk AS (
    SELECT
        cik,
        filing_date,
        risk_term_count,
        top_terms,
        risk_word_count
    FROM {{ source('sec_filings', 'fact_risk') }}
),

risk_drift AS (
    SELECT
        cik,
        filing_date,
        risk_cosine_distance
    FROM {{ source('sec_filings', 'fact_risk_drift') }}
),

market AS (
    SELECT
        cik,
        filing_date,
        return_1d,
        return_5d,
        return_20d,
        volatility_20d
    FROM {{ source('sec_filings', 'fact_market_reaction') }}
),

joined AS (
    SELECT
        b.*,

        lm.optimism_per_1k_avg,
        lm.caution_per_1k_avg,
        lm.concern_per_1k_avg,
        lm.optimism_share_avg,
        lm.caution_share_avg,
        lm.concern_share_avg,

        CASE
            WHEN lm.optimism_share_avg IS NULL THEN NULL
            WHEN lm.optimism_share_avg >= lm.caution_share_avg
             AND lm.optimism_share_avg >= lm.concern_share_avg
                THEN 'optimism'
            WHEN lm.caution_share_avg >= lm.concern_share_avg
                THEN 'caution'
            ELSE 'concern'
        END AS dominant_narrative,

        fb.finbert_mgmt_score,
        fb.finbert_risk_score,
        fb.finbert_risk_negative_prob,

        r.risk_term_count,
        r.top_terms,
        r.risk_word_count,
        CASE WHEN r.risk_word_count > 0
             THEN r.risk_term_count * 1000.0 / r.risk_word_count
        END AS risk_density_per_1k,
        rd.risk_cosine_distance,

        m.return_1d,
        m.return_5d,
        m.return_20d,
        m.volatility_20d

    FROM base b
    LEFT JOIN lm_managerial_agg lm ON b.cik = lm.cik AND b.filing_date = lm.filing_date
    LEFT JOIN finbert fb           ON b.cik = fb.cik AND b.filing_date = fb.filing_date
    LEFT JOIN risk r               ON b.cik = r.cik  AND b.filing_date = r.filing_date
    LEFT JOIN risk_drift rd        ON b.cik = rd.cik AND b.filing_date = rd.filing_date
    LEFT JOIN market m             ON b.cik = m.cik  AND b.filing_date = m.filing_date
),

-- computed BEFORE the drift filter so a company's first filing can serve as the "previous" one
with_change AS (
    SELECT
        *,
        risk_density_per_1k
          - LAG(risk_density_per_1k) OVER (PARTITION BY cik ORDER BY filing_date) AS risk_density_change
    FROM joined
),

comparable AS (
    SELECT
        *,
        COUNT(*) OVER (PARTITION BY cik) AS valid_filing_count
    FROM with_change
    WHERE risk_cosine_distance IS NOT NULL
)

SELECT *
FROM comparable
WHERE valid_filing_count > 1
