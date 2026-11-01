from datetime import date

import pytest

from trading_sentiment import edgar

TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    "2": {"cik_str": 1652044, "ticker": "GOOG", "title": "Alphabet Inc."},
}

SUBMISSIONS = {
    "cik": 320193,
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {"recent": {
        "form": ["10-K", "8-K", "10-Q", "10-K"],
        "filingDate": ["2024-11-01", "2024-10-01", "2024-08-02", "2019-10-31"],
        "accessionNumber": ["0000320193-24-000123", "0000320193-24-000100", "0000320193-24-000081", "0000320193-19-000119"],
        "primaryDocument": ["aapl-20240928.htm", "x.htm", "aapl-20240629.htm", "a10-k2019.htm"],
    }},
}


def test_parse_company_tickers_one_row_per_cik_with_deterministic_primary_ticker():
    rows = edgar.parse_company_tickers(TICKERS)
    assert [r["cik"] for r in rows] == ["0000320193", "0001652044"]
    assert rows[1]["tickers"] == "GOOG"


def test_filings_from_submissions_filters_form_and_date():
    rows = edgar.filings_from_submissions(SUBMISSIONS, forms=("10-K",), since=date(2020, 1, 1))
    assert len(rows) == 1
    row = rows[0]
    assert row["filing_date"] == date(2024, 11, 1)
    assert row["filing_url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
    assert row["tickers"] == "AAPL" and row["cik"] == "0000320193"


def test_filings_can_include_10q():
    rows = edgar.filings_from_submissions(SUBMISSIONS, forms=("10-K", "10-Q"))
    assert {r["form_type"] for r in rows} == {"10-K", "10-Q"}


@pytest.mark.parametrize("ua", [None, "", "no-contact-info"])
def test_user_agent_must_contain_contact_email(ua):
    with pytest.raises(ValueError):
        edgar.require_user_agent(ua)


class Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Http:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, headers, timeout):
        self.calls += 1
        assert "@" in headers["User-Agent"]
        return self.responses.pop(0)


def test_fetch_json_retries_rate_limits_then_succeeds():
    http = Http(Resp(429), Resp(503), Resp(200, {"ok": True}))
    assert edgar.fetch_json("u", "Jo jo@example.com", session=http, sleep=lambda s: None) == {"ok": True}
    assert http.calls == 3


def test_fetch_json_does_not_retry_client_errors():
    http = Http(Resp(404))
    with pytest.raises(RuntimeError):
        edgar.fetch_json("u", "Jo jo@example.com", session=http, sleep=lambda s: None)
    assert http.calls == 1
