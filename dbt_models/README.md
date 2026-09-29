# dbt models

Staging and mart models over the Delta tables written by the Databricks notebooks in `../databricks_notebooks/`.

| Layer | Model | Materialisation | Purpose |
|---|---|---|---|
| staging | `stg_cleaned_filings` | view | 10-K filings with non-empty Risk Factors and MD&A (input of notebook 03, base of the mart) |
| staging | `stg_clean_10Ks` | view | filings whose three sections each exceed 5,000 characters (input of notebooks 04-07) |
| marts | `comp_kpi_filing` | table | one KPI row per comparable filing: sentiment, risk, drift, market reaction |

## Run order (notebooks and dbt alternate)

```text
notebooks 01, 02  ->  dbt build --select staging  ->  notebooks 03-07  ->  dbt build --select marts
```

## Setup

```bash
pip install dbt-databricks          # dbt >= 1.10.5
cp profiles.example.yml ~/.dbt/profiles.yml     # then export DATABRICKS_HOST / HTTP_PATH / TOKEN
dbt deps
dbt build --select staging
dbt build --select marts
```

## Tests without Databricks

`ci/profiles.yml` runs the same models on DuckDB against small fixture tables
(`tests/test_dbt_marts.py` from the repository root builds them, runs `dbt build` and checks the mart output).
