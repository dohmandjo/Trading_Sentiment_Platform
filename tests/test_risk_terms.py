import pytest

spacy = pytest.importorskip("spacy")

from trading_sentiment import risk_terms as rt  # noqa: E402

try:
    NLP = spacy.load("en_core_web_sm")
except OSError:  # pragma: no cover
    pytest.skip("run: python -m spacy download en_core_web_sm", allow_module_level=True)

MATCHER = rt.build_matcher(NLP)


def count(text):
    return rt.count_risk_terms(text, NLP, MATCHER)


def test_multi_word_keywords_now_match():
    """Regression: 'interest rates', 'supply chain' and 'data breach' could never match before."""
    freq = count("Rising interest rates and a supply chain failure could cause a data breach.")
    assert freq["interest rates"] == 1
    assert freq["supply chain"] == 1
    assert freq["data breach"] == 1


def test_lemmas_and_case_are_normalised():
    freq = count("Data Breaches and cyber ransomware. Interest Rate moves. Litigations.")
    assert freq["data breach"] == 1
    assert freq["interest rates"] == 1
    assert freq["litigation"] == 1


def test_empty_text_gives_no_terms():
    assert count("") == {} and count(None) == {}


def test_summary_orders_by_count_then_name_and_counts_words():
    text = "risk risk risk litigation litigation compliance regulation"
    s = rt.summarize(count(text), text)
    assert s["top_terms"] == ["risk", "litigation", "compliance"]
    assert s["risk_term_count"] == 7 and s["risk_word_count"] == 7
