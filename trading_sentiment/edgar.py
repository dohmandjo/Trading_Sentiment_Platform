"""SEC EDGAR helpers used by notebook 01.

The functions that only reshape JSON are pure and unit-tested; ``fetch_json`` is the only one that touches the network.
SEC fair-access policy: identify yourself in the User-Agent and stay below 10 requests per second.
"""
from __future__ import annotations

import time
from datetime import date

import requests

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{document}"
MIN_INTERVAL_SECONDS = 0.12  # ~8 requests/second, under the SEC limit of 10


def require_user_agent(user_agent: str | None) -> str:
    """SEC blocks anonymous clients; the header must look like 'Name name@example.com'."""
    if not user_agent or "@" not in user_agent:
        raise ValueError("Set a User-Agent that contains your contact e-mail, e.g. 'Jane Doe jane@example.com'.")
    return user_agent


def fetch_json(url: str, user_agent: str, retries: int = 3, session=None, sleep=time.sleep) -> dict:
    """GET a JSON document politely: throttle, and retry rate-limit / server errors with backoff."""
    http = session or requests
    headers = {"User-Agent": require_user_agent(user_agent)}
    for attempt in range(retries + 1):
        sleep(MIN_INTERVAL_SECONDS)
        resp = http.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        retryable = resp.status_code == 429 or resp.status_code >= 500
        if not retryable or attempt == retries:
            resp.raise_for_status()
        sleep(2**attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def cik10(value) -> str:
    """Zero-padded 10-digit CIK, the form used by the submissions API."""
    return str(int(value)).zfill(10)


def primary_ticker(tickers) -> str | None:
    """Deterministic 'main' ticker of a company (alphabetically first, so GOOG wins over GOOGL)."""
    tickers = [t for t in (tickers or []) if t]
    return sorted(tickers)[0] if tickers else None


def parse_company_tickers(payload: dict) -> list[dict]:
    """``company_tickers.json`` -> one row per CIK with its primary ticker.

    The file maps "0", "1", ... to {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}; companies with
    several share classes appear several times.
    """
    tickers_by_cik: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for item in payload.values():
        cik = cik10(item["cik_str"])
        tickers_by_cik.setdefault(cik, []).append(item["ticker"])
        names[cik] = item.get("title", "")
    return [
        {"cik": cik, "company_name": names[cik], "tickers": primary_ticker(ts)}
        for cik, ts in sorted(tickers_by_cik.items())
    ]


def filings_from_submissions(payload: dict, forms=("10-K",), since: date | None = None) -> list[dict]:
    """Recent filings of the requested form types from a ``CIK##########.json`` submissions document.

    Only the ``recent`` block is read (about a thousand latest filings), which covers five years of 10-Ks for
    normal filers.
    """
    recent = payload.get("filings", {}).get("recent", {})
    cik = cik10(payload["cik"])
    rows = []
    for i, form in enumerate(recent.get("form", [])):
        if form not in forms:
            continue
        filed = date.fromisoformat(recent["filingDate"][i])
        if since and filed < since:
            continue
        accession = recent["accessionNumber"][i]
        document = recent["primaryDocument"][i]
        rows.append(
            {
                "cik": cik,
                "company_name": payload.get("name"),
                "tickers": primary_ticker(payload.get("tickers")),
                "form_type": form,
                "filing_date": filed,
                "accessionNumber": accession,
                "filing_url": ARCHIVES_URL.format(
                    cik_int=int(cik), accession_nodash=accession.replace("-", ""), document=document
                ),
            }
        )
    return rows
