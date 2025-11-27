<<<<<<< HEAD
SELECT cik, company_name, tickers, filing_date, accessionNumber, market_cap, risks_text, mda_text
FROM {{ source("sec_filings","top100_clean_filing") }}
WHERE length(trim(risks_text)) > 0 AND length(trim(mda_text)) > 0;
=======
SELECT cik, company_name, filing_date, risks_text, mda_text
FROM {{ source("sec_filings","clean_filing_doc") }}
WHERE risks_text!="" AND mda_text!="";
>>>>>>> f3329cd7980a85d7583c39723d02d71b1bf1878c
