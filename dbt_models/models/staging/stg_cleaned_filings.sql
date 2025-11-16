SELECT cik, company_name, filing_date, risks_text, mda_text
FROM {{ source("sec_filings","clean_filing_doc") }};