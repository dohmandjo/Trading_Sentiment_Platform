import pytest

from trading_sentiment import sentiment

FINBERT_ID2LABEL = {0: "positive", 1: "negative", 2: "neutral"}   # ProsusAI/finbert config.json


def test_chunking_covers_all_tokens_when_under_the_cap():
    chunks = sentiment.chunk_token_ids(list(range(1200)), size=510, max_chunks=32)
    assert [len(c) for c in chunks] == [510, 510, 180]
    assert sum(chunks, []) == list(range(1200))


def test_chunking_samples_evenly_across_the_whole_text_when_over_the_cap():
    ids = list(range(100 * 10))
    chunks = sentiment.chunk_token_ids(ids, size=10, max_chunks=5)
    assert len(chunks) == 5
    starts = [c[0] for c in chunks]
    assert starts == [0, 200, 400, 600, 800]     # not just the first five chunks


def test_chunking_rejects_bad_arguments():
    with pytest.raises(ValueError):
        sentiment.chunk_token_ids([1], size=0)


def test_labels_follow_the_model_config_not_a_hard_coded_order():
    """Regression: with output [pos, neg, neu] the old code reported neutral=neg and negative=neu."""
    out = sentiment.finbert_summary([0.1, 0.7, 0.2], FINBERT_ID2LABEL)
    assert out["negative_prob"] == pytest.approx(0.7)
    assert out["neutral_prob"] == pytest.approx(0.2)
    assert out["positive_prob"] == pytest.approx(0.1)
    assert out["sentiment_label"] == "negative"
    assert out["sentiment_score"] == pytest.approx(0.1 - 0.7)


def test_unknown_label_set_is_rejected():
    with pytest.raises(ValueError):
        sentiment.named_probabilities([0.5, 0.5], {0: "positive", 1: "negative"})


def test_mean_probabilities():
    assert sentiment.mean_probabilities([[1, 0, 0], [0, 1, 0]]) == [0.5, 0.5, 0.0]
    with pytest.raises(ValueError):
        sentiment.mean_probabilities([])


def test_lm_shares_sum_to_one_and_survive_empty_sections():
    s = sentiment.lm_shares(optimism=2, caution=1, concern=1, tokens=2000)
    assert s["optimism_share"] + s["caution_share"] + s["concern_share"] == pytest.approx(1)
    assert s["optimism_per_1k"] == pytest.approx(1.0)
    empty = sentiment.lm_shares(0, 0, 0, 0)
    assert all(v is None for v in empty.values())
