SELECT cik, company_name, tickers, filing_date, accessionNumber, market_cap, sector, filing_url, bus_text, risks_text, mda_text
FROM {{ source("sec_filings","filings_10K_text")}}
WHERE length(trim(bus_text)) > 5000 AND length(trim(risks_text)) > 5000 AND length(trim(mda_text)) > 5000;


