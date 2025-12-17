WITH base AS (
    SELECT
        f.cik,
        f.company_name,
        f.tickers,
        f.filing_date,
        f.accessionNumber,
        f.form_type,
        f.market_cap,
        f.sector
    FROM {{ ref('stg_cleaned_filings') }} f
    WHERE f.form_type = '10-K'
),

lm_managerial AS (
    SELECT
        cik,
        filing_date,
        optimism_per_1k,
        caution_per_1k,
        concern_per_1k,
        optimism_share,
        caution_share,
        concern_share
    FROM {{ source('sec_filings', 'fact_lm_sentiment') }}
    WHERE section_name IN ('BUSINESS', 'MDA')
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
    FROM lm_managerial
    GROUP BY cik, filing_date
),

risk AS (
    SELECT
        cik,
        filing_date,
        risk_term_count,
        top_terms
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
            WHEN lm.optimism_share_avg >= lm.caution_share_avg
             AND lm.optimism_share_avg >= lm.concern_share_avg
                THEN 'optimism'
            WHEN lm.caution_share_avg >= lm.concern_share_avg
                THEN 'caution'
            ELSE 'concern'
        END AS dominant_narrative,

        r.risk_term_count,
        r.top_terms,
        rd.risk_cosine_distance,

        m.return_1d,
        m.return_5d,
        m.return_20d,
        m.volatility_20d

    FROM base b
    LEFT JOIN lm_managerial_agg lm
        ON b.cik = lm.cik
       AND b.filing_date = lm.filing_date
    LEFT JOIN risk r
        ON b.cik = r.cik
       AND b.filing_date = r.filing_date
    LEFT JOIN risk_drift rd
        ON b.cik = rd.cik
       AND b.filing_date = rd.filing_date
    LEFT JOIN market m
        ON b.cik = m.cik
       AND b.filing_date = m.filing_date

    WHERE rd.risk_cosine_distance IS NOT NULL
)

SELECT *
FROM (
    SELECT
        *,
        COUNT(*) OVER (PARTITION BY cik) AS valid_filing_count
    FROM joined
)
WHERE valid_filing_count > 1
;
