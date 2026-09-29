"""Build the dbt project on DuckDB with fixture tables and check the mart (runs `dbt build`, incl. all dbt tests).

Skipped when dbt-duckdb is not installed. Needs network access for `dbt deps` (dbt_utils).
"""
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")
pytest.importorskip("dbt.adapters.duckdb")

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "dbt_models"
LONG_TEXT = "word " * 2000       # 10,000 characters > the 5,000-character staging threshold


def build_fixtures(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS sec_filings")
    con.execute("""
        CREATE TABLE sec_filings.filings_10K_text (
            cik VARCHAR, company_name VARCHAR, tickers VARCHAR, form_type VARCHAR, filing_date DATE,
            accessionNumber VARCHAR, market_cap BIGINT, sector VARCHAR, filing_url VARCHAR,
            bus_text VARCHAR, risks_text VARCHAR, mda_text VARCHAR)""")
    filings = [   # (cik, name, date, business text)
        ("0000000001", "ACME", date(2021, 2, 1), LONG_TEXT), ("0000000001", "ACME", date(2022, 2, 1), LONG_TEXT),
        ("0000000001", "ACME", date(2023, 2, 1), LONG_TEXT), ("0000000001", "ACME", date(2024, 2, 1), LONG_TEXT),
        ("0000000002", "BETA", date(2023, 2, 1), LONG_TEXT), ("0000000002", "BETA", date(2024, 2, 1), LONG_TEXT),
        ("0000000003", "GAMMA", date(2024, 2, 1), "too short"),
    ]
    for cik, name, filed, bus in filings:
        con.execute("INSERT INTO sec_filings.filings_10K_text VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [cik, name, name[:3], "10-K", filed, f"{cik}-{filed}", 1_000, "Tech", "http://x", bus, LONG_TEXT, LONG_TEXT])

    con.execute("""CREATE TABLE sec_filings.fact_risk (cik VARCHAR, filing_date DATE, risk_term_count INTEGER,
                   top_terms VARCHAR[], risk_word_count INTEGER)""")
    # ACME: density (per 1k words) 10, 20, 15, 30
    for filed, count in ((date(2021, 2, 1), 10), (date(2022, 2, 1), 20), (date(2023, 2, 1), 15), (date(2024, 2, 1), 30)):
        con.execute("INSERT INTO sec_filings.fact_risk VALUES ('0000000001', ?, ?, ['risk'], 1000)", [filed, count])
    con.execute("INSERT INTO sec_filings.fact_risk VALUES ('0000000002', DATE '2024-02-01', 5, ['risk'], 0)")

    con.execute("CREATE TABLE sec_filings.fact_risk_drift (cik VARCHAR, filing_date DATE, risk_cosine_distance DOUBLE)")
    for cik, filed, dist in (("0000000001", date(2022, 2, 1), 0.10), ("0000000001", date(2023, 2, 1), 0.25),
                             ("0000000001", date(2024, 2, 1), 0.05), ("0000000002", date(2024, 2, 1), 0.30)):
        con.execute("INSERT INTO sec_filings.fact_risk_drift VALUES (?,?,?)", [cik, filed, dist])

    con.execute("""CREATE TABLE sec_filings.fact_lm_sentiment (cik VARCHAR, filing_date DATE, section_name VARCHAR,
                   optimism_per_1k DOUBLE, caution_per_1k DOUBLE, concern_per_1k DOUBLE,
                   optimism_share DOUBLE, caution_share DOUBLE, concern_share DOUBLE)""")
    lm = {  # 2022: optimism wins; 2023: caution wins; 2024: concern wins.  RISKS rows must not influence the result
        date(2022, 2, 1): (0.6, 0.3, 0.1), date(2023, 2, 1): (0.2, 0.6, 0.2), date(2024, 2, 1): (0.1, 0.2, 0.7)}
    for filed, (o, c, n) in lm.items():
        for section in ("BUSINESS", "MDA"):
            con.execute("INSERT INTO sec_filings.fact_lm_sentiment VALUES ('0000000001',?,?,1,1,1,?,?,?)", [filed, section, o, c, n])
        con.execute("INSERT INTO sec_filings.fact_lm_sentiment VALUES ('0000000001',?,'RISKS',1,1,1,0,0,1)", [filed])

    con.execute("""CREATE TABLE sec_filings.fact_finbert_sentiment (cik VARCHAR, filing_date DATE, section_name VARCHAR,
                   sentiment_score DOUBLE, negative_prob DOUBLE)""")
    for section, score, neg in (("BUSINESS", 0.2, 0.1), ("MDA", 0.4, 0.1), ("RISKS", -0.5, 0.7)):
        con.execute("INSERT INTO sec_filings.fact_finbert_sentiment VALUES ('0000000001', DATE '2023-02-01', ?, ?, ?)", [section, score, neg])

    con.execute("""CREATE TABLE sec_filings.fact_market_reaction (cik VARCHAR, filing_date DATE, return_1d DOUBLE,
                   return_5d DOUBLE, return_20d DOUBLE, volatility_20d DOUBLE)""")
    con.execute("INSERT INTO sec_filings.fact_market_reaction VALUES ('0000000001', DATE '2023-02-01', 0.01, 0.02, 0.03, 0.2)")


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    db = tmp_path_factory.mktemp("dbt") / "ci.duckdb"
    con = duckdb.connect(str(db))
    build_fixtures(con)
    con.close()
    env = {**os.environ, "DBT_DUCKDB_PATH": str(db), "DBT_SEND_ANONYMOUS_USAGE_STATS": "false"}
    base = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    args = ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR / "ci")]
    commands = [["build"]] if (DBT_DIR / "dbt_packages" / "dbt_utils").exists() else [["deps"], ["build"]]
    for cmd in commands:
        result = subprocess.run([*base, *cmd, *args], env=env, capture_output=True, text=True, cwd=DBT_DIR)
        assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    con = duckdb.connect(str(db), read_only=True)
    yield con
    con.close()


def test_mart_keeps_only_comparable_filings_of_companies_with_a_trend(warehouse):
    rows = warehouse.execute("SELECT cik, filing_date FROM sec_filings.comp_kpi_filing ORDER BY filing_date").fetchall()
    assert rows == [("0000000001", date(2022, 2, 1)), ("0000000001", date(2023, 2, 1)), ("0000000001", date(2024, 2, 1))]


def test_dominant_narrative_uses_business_and_mda_only(warehouse):
    got = dict(warehouse.execute("SELECT filing_date, dominant_narrative FROM sec_filings.comp_kpi_filing").fetchall())
    assert got == {date(2022, 2, 1): "optimism", date(2023, 2, 1): "caution", date(2024, 2, 1): "concern"}


def test_risk_density_and_change_use_the_previous_filing_even_when_it_is_not_in_the_mart(warehouse):
    got = warehouse.execute(
        "SELECT filing_date, risk_density_per_1k, risk_density_change FROM sec_filings.comp_kpi_filing ORDER BY 1").fetchall()
    assert got == [(date(2022, 2, 1), 20.0, 10.0), (date(2023, 2, 1), 15.0, -5.0), (date(2024, 2, 1), 30.0, 15.0)]


def test_finbert_scores_are_split_between_management_and_risk_sections(warehouse):
    mgmt, risk, neg = warehouse.execute(
        "SELECT finbert_mgmt_score, finbert_risk_score, finbert_risk_negative_prob FROM sec_filings.comp_kpi_filing "
        "WHERE filing_date = DATE '2023-02-01'").fetchone()
    assert (round(mgmt, 6), risk, neg) == (0.3, -0.5, 0.7)


def test_staging_filters(warehouse):
    assert warehouse.execute("SELECT count(*) FROM sec_filings.stg_clean_10Ks").fetchone()[0] == 6          # GAMMA is too short
    assert warehouse.execute("SELECT count(*) FROM sec_filings.stg_cleaned_filings").fetchone()[0] == 7     # looser filter
