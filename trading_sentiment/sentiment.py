"""Sentiment helpers: FinBERT on long text (notebook 04) and Loughran-McDonald buckets (notebook 05)."""
from __future__ import annotations

from collections.abc import Sequence

MAX_MODEL_TOKENS = 512          # BERT limit, including [CLS] and [SEP]
CHUNK_TOKENS = MAX_MODEL_TOKENS - 2
DEFAULT_MAX_CHUNKS = 32         # per section; keeps CPU inference of ~300 filings x 3 sections tractable


def chunk_token_ids(ids: Sequence[int], size: int = CHUNK_TOKENS, max_chunks: int = DEFAULT_MAX_CHUNKS) -> list[list[int]]:
    """Split token ids into model-sized chunks; when there are too many, keep an evenly spaced sample.

    Scoring only the first 512 tokens (the previous behaviour) meant a 40,000-word Risk Factors section was judged by
    its first ~350 words. Sampling evenly covers the whole section at a bounded cost.
    """
    if size < 1 or max_chunks < 1:
        raise ValueError("size and max_chunks must be positive")
    chunks = [list(ids[i : i + size]) for i in range(0, len(ids), size)]
    if len(chunks) <= max_chunks:
        return chunks
    step = len(chunks) / max_chunks
    return [chunks[int(i * step)] for i in range(max_chunks)]


def mean_probabilities(rows: Sequence[Sequence[float]]) -> list[float]:
    """Column-wise mean of per-chunk class probabilities."""
    if not rows:
        raise ValueError("no probabilities to average")
    n = len(rows)
    return [sum(row[j] for row in rows) / n for j in range(len(rows[0]))]


def named_probabilities(probs: Sequence[float], id2label: dict) -> dict[str, float]:
    """Map model output positions to class names using the model's own config.

    ProsusAI/finbert orders its classes ``positive, negative, neutral``. The old code assumed
    ``positive, neutral, negative``, which swapped the negative and neutral probabilities and made the compound score
    ``P(positive) - P(neutral)``. Always read ``model.config.id2label`` instead of hard-coding the order.
    """
    named = {str(id2label[i]).lower(): float(p) for i, p in enumerate(probs)}
    missing = {"positive", "negative", "neutral"} - named.keys()
    if missing:
        raise ValueError(f"model labels {sorted(named)} do not contain {sorted(missing)}")
    return named


def finbert_summary(probs: Sequence[float], id2label: dict) -> dict:
    """Averaged class probabilities -> label + compound score (P(positive) - P(negative))."""
    named = named_probabilities(probs, id2label)
    label = max(named, key=named.get)
    return {
        "positive_prob": named["positive"],
        "negative_prob": named["negative"],
        "neutral_prob": named["neutral"],
        "sentiment_label": label,
        "sentiment_score": named["positive"] - named["negative"],
    }


def lm_shares(optimism: float, caution: float, concern: float, tokens: float) -> dict:
    """Loughran-McDonald bucket intensities and shares; None instead of dividing by zero.

    Databricks serverless runs Spark in ANSI mode, where ``x / 0`` raises an error instead of returning NULL.
    """
    signal = optimism + caution + concern
    per_1k = tokens / 1000.0
    return {
        "optimism_per_1k": optimism / per_1k if per_1k else None,
        "caution_per_1k": caution / per_1k if per_1k else None,
        "concern_per_1k": concern / per_1k if per_1k else None,
        "optimism_share": optimism / signal if signal else None,
        "caution_share": caution / signal if signal else None,
        "concern_share": concern / signal if signal else None,
    }
