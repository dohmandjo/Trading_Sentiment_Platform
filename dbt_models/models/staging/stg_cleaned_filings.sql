-- Filings whose Risk Factors and MD&A sections were extracted (any length above zero).
-- Input for notebook 03 and the base of the KPI mart.
SELECT
    cik,
    company_name,
    tickers,
    filing_date,
    accessionNumber,
    form_type,
    market_cap,
    sector,
    risks_text,
    mda_text
FROM {{ source('sec_filings', 'filings_10K_text') }}
WHERE length(trim(risks_text)) > 0
  AND length(trim(mda_text)) > 0
