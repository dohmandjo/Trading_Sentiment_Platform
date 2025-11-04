SELECT id, company, form_type, filing_date, text
FROM {{ source('sec_filings', 'raw_filings') }};
