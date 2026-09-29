"""Risk-term counting for the Risk Factors section (notebook 03)."""
from __future__ import annotations

RISK_KEYWORDS = [
    "risk", "inflation", "liability", "default", "fraud",
    "recession", "unemployment", "interest rates", "currency fluctuations",
    "tariffs", "trade restrictions", "geopolitical tensions", "conflict", "terrorism",
    "natural disasters", "earthquakes", "climate change", "extreme weather",
    "public health", "pandemic",
    "supply chain", "component shortages", "manufacturing disruption", "logistics",
    "cybersecurity", "ransomware", "data breach", "unauthorized access",
    "competition", "margin pressure", "obsolescence", "innovation",
    "regulation", "litigation", "intellectual property", "compliance",
    "credit risk", "liquidity",
    "labor disputes", "talent retention",
    "product defects", "recall", "quality issues",
]


def word_count(text: str | None) -> int:
    return len(text.split()) if text else 0


def build_matcher(nlp, keywords=RISK_KEYWORDS):
    """spaCy PhraseMatcher on lemmas, so 'interest rates' matches 'interest rate' and 'Interest Rates'.

    The previous implementation compared each single-token lemma with the keyword list, so the 17 multi-word
    keywords ('supply chain', 'data breach', ...) could never match.
    """
    from spacy.matcher import PhraseMatcher

    matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    for keyword in keywords:
        matcher.add(keyword, [nlp(keyword)])
    return matcher


def count_risk_terms(text: str | None, nlp, matcher) -> dict[str, int]:
    """Occurrences of each keyword in ``text`` (empty dict for empty text)."""
    if not text or not text.strip():
        return {}
    # spaCy's lemmatizer is case-sensitive ('Litigations' stays 'Litigations' at the start of a sentence)
    doc = nlp(text.lower())
    freq: dict[str, int] = {}
    for match_id, _start, _end in matcher(doc):
        key = nlp.vocab.strings[match_id]
        freq[key] = freq.get(key, 0) + 1
    return freq


def summarize(freq: dict[str, int], text: str | None, top_n: int = 3) -> dict:
    """Row for ``fact_risk``: total count, top terms (ties broken alphabetically) and length in words."""
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "risk_term_count": int(sum(freq.values())),
        "top_terms": [term for term, _ in ranked[:top_n]],
        "risk_word_count": word_count(text),
    }
