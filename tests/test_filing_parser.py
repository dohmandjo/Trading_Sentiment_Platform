import pytest

pytest.importorskip("bs4")

from trading_sentiment import filing_parser as fp  # noqa: E402

BUS = "We design and sell widgets around the world. " * 30
RISK = "Our results could be harmed by supply chain disruption. " * 30
MDA = "Revenue grew because demand for widgets increased. " * 30

HTML = f"""
<html><body>
<table><tr><td>Item 1. Business</td><td>3</td></tr><tr><td>Item 1A. Risk Factors</td><td>9</td></tr></table>
<p>PART I</p>
<p>Item&nbsp;1. Business</p><p><ix:nonnumeric name="x">{BUS}</ix:nonnumeric></p>
<p>Item 1A. Risk Factors</p><p>{RISK}</p>
<p>Item 1B. Unresolved Staff Comments</p><p>None.</p>
<p>Item 7. Management’s Discussion and Analysis of Financial Condition</p><p>{MDA}</p>
<p>Item 7A. Quantitative and Qualitative Disclosures</p>
<script>var ignored = 1;</script>
</body></html>
"""


def test_sections_are_extracted_and_toc_table_is_ignored():
    _full, business, risk, mda = fp.parse_filing_html(HTML)
    assert business.startswith("WE DESIGN AND SELL WIDGETS") and "SUPPLY CHAIN" not in business
    assert risk.startswith("OUR RESULTS COULD BE HARMED") and "UNRESOLVED" not in risk
    assert "REVENUE GREW" in mda and "QUANTITATIVE" not in mda
    assert "IGNORED" not in _full


def test_spaced_out_headings_are_normalised():
    text = "ITEM 1A. R I S K   F A C T O R S body text here ITEM 1B. next"
    assert "ITEM 1A. RISK FACTORS" in fp.normalize_headers(text)


def test_missing_sections_are_empty_strings_not_errors():
    assert fp.extract_sections("just some prose without any headings") == ("", "", "")


def test_parse_filing_url_returns_empty_fields_on_network_failure(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    assert fp.parse_filing_url("http://x", "Jo jo@example.com", sleep=lambda s: None) == ("", "", "", "")


def test_paragraph_table_of_contents_is_not_mistaken_for_the_section():
    """Regression: with a TOC written as text (not a <table>) the first match was the TOC entry."""
    text = ("ITEM 1. BUSINESS 3 ITEM 1A. RISK FACTORS 9 ITEM 1B. UNRESOLVED 20 "
            f"ITEM 1. BUSINESS {BUS} ITEM 1A. RISK FACTORS {RISK} ITEM 1B. UNRESOLVED STAFF COMMENTS NONE")
    business, risk, _mda = fp.extract_sections(text)
    assert business.upper() == BUS.upper().strip()
    assert risk.upper() == RISK.upper().strip()


class _Resp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_parse_filing_url_retries_rate_limits(monkeypatch):
    import requests

    responses = [_Resp(429), _Resp(503), _Resp(200, HTML)]
    monkeypatch.setattr(requests, "get", lambda *a, **k: responses.pop(0))
    _full, business, risk, mda = fp.parse_filing_url("http://x", "Jo jo@example.com", sleep=lambda s: None)
    assert not responses and business and risk and mda


def test_parse_filing_url_does_not_retry_client_errors(monkeypatch):
    import requests

    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **k: calls.append(1) or _Resp(404))
    assert fp.parse_filing_url("http://x", "Jo jo@example.com", sleep=lambda s: None) == ("", "", "", "")
    assert len(calls) == 1
