import numpy as np
import pandas as pd
import pytest

from trading_sentiment import market


def series(n=30, start="2024-02-20", growth=1.01):
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * growth ** np.arange(n), index=idx, name="Close")


def test_reaction_uses_first_close_on_or_after_filing_date():
    prices = series()
    out = market.reaction_from_prices(prices, "2024-02-24")     # a Saturday -> base is Monday 26th
    base = prices.loc["2024-02-26"]
    assert out["return_1d"] == pytest.approx(prices.loc["2024-02-27"] / base - 1)
    assert out["return_5d"] == pytest.approx(prices.iloc[prices.index.get_loc(pd.Timestamp("2024-02-26")) + 5] / base - 1)
    assert out["volatility_20d"] == pytest.approx(0.0, abs=1e-9)  # constant growth -> no dispersion


def test_reaction_is_none_when_history_is_too_short():
    out = market.reaction_from_prices(series(n=4), "2024-02-20")
    assert out["return_1d"] is not None
    assert out["return_5d"] is None and out["return_20d"] is None


def test_reaction_with_no_prices_or_future_filing():
    assert market.reaction_from_prices(pd.Series(dtype=float), "2024-01-01") == market.NO_REACTION
    assert market.reaction_from_prices(series(), "2030-01-01") == market.NO_REACTION


def test_extract_close_handles_flat_and_multiindex_frames():
    idx = pd.bdate_range("2024-01-02", periods=3)
    flat = pd.DataFrame({"Open": [1, 2, 3], "Close": [10.0, 11.0, 12.0]}, index=idx)
    multi = flat.copy()
    multi.columns = pd.MultiIndex.from_product([flat.columns, ["NVDA"]])
    assert market.extract_close(flat).tolist() == [10.0, 11.0, 12.0]
    assert market.extract_close(multi).tolist() == [10.0, 11.0, 12.0]
    assert market.extract_close(pd.DataFrame()).empty
