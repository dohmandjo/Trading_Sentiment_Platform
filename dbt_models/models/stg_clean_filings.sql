SELECT cik, company_name, filing_date, risks_text, mda_text
FROM {{ source("sec_filing","clean_filing_doc") }};