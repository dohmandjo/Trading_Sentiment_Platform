"""Split an SEC 10-K HTML document into Business, Risk Factors and MD&A text (notebook 02).

The heuristics are those of the original notebook (first heading match after normalising the headings); they were
moved here unchanged so they can be tested. Known limits are listed in the README.
"""
from __future__ import annotations

import re

MDA_HEADING = "ITEM 7. MANAGEMENT’S DISCUSSION AND ANALYSIS"


def clean_inline_xbrl(html: str) -> str:
    """HTML -> plain text: unwrap inline-XBRL tags, drop scripts, styles and tables, squeeze whitespace."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(re.compile("^ix:")):
        tag.unwrap()
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True).replace(" ", " ")
    return re.sub(r"\s+", " ", text)


def _loose(word: str) -> str:
    """Allow any spacing between letters (some filings render headings as 'B U S I N E S S')."""
    return "".join(ch + r"\s*" for ch in word)


def normalize_headers(text: str) -> str:
    """Upper-case and rewrite the three headings we need into a canonical form."""
    t = text.upper()
    t = re.sub(rf"ITEM\s*1\s*[\.\-]?\s*{_loose('BUSINESS')}", "ITEM 1. BUSINESS", t)
    t = re.sub(rf"ITEM\s*1A\s*[\.\-]?\s*{_loose('RISKFACTORS')}", "ITEM 1A. RISK FACTORS", t)
    t = re.sub(
        rf"ITEM\s*7\s*[\.\-]?\s*{_loose('MANAGEMENT')}[^\n]{{0,80}}?{_loose('DISCUSSION')}[^\n]{{0,80}}?{_loose('ANALYSIS')}",
        MDA_HEADING,
        t,
    )
    return t


def _section(text: str, start: str, end_lookahead: str) -> str:
    m = re.search(rf"{start}(.*?)(?={end_lookahead})", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_sections(text: str) -> tuple[str, str, str]:
    """(business, risk_factors, mda) from already cleaned text; '' for a section that was not found."""
    u = normalize_headers(text)
    business = _section(u, r"ITEM 1\. BUSINESS", r"ITEM 1A\. RISK FACTORS|ITEM 1B\.|ITEM 2\.")
    risk = _section(u, r"ITEM 1A\. RISK FACTORS", r"ITEM 1B\.|ITEM 2\.|ITEM 3\.")
    mda = _section(u, re.escape(MDA_HEADING), r"ITEM 7A\.|ITEM 8\.|PART III")
    return business, risk, mda


def parse_filing_html(html: str) -> tuple[str, str, str, str]:
    """(normalised full text, business, risk_factors, mda)."""
    cleaned = clean_inline_xbrl(html)
    business, risk, mda = extract_sections(cleaned)
    return normalize_headers(cleaned), business, risk, mda


def parse_filing_url(url: str, user_agent: str, timeout: int = 20) -> tuple[str, str, str, str]:
    """Download one filing and parse it; a failed download or parse yields four empty strings (filtered later by dbt)."""
    import requests

    try:
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
        resp.raise_for_status()
        return parse_filing_html(resp.text)
    except Exception as exc:  # one bad filing must not fail the whole Spark job
        print(f"Could not parse {url}: {exc}")
        return "", "", "", ""
