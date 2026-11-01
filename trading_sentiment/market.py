"""Market-cap and post-filing price-reaction helpers (notebooks 01 and 07)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

NO_REACTION = {"return_1d": None, "return_5d": None, "return_20d": None, "volatility_20d": None}


def extract_close(downloaded: pd.DataFrame) -> pd.Series:
    """The 'Close' prices as one Series, whatever shape yfinance returned.

    Recent yfinance versions return MultiIndex columns ``(field, ticker)`` even for a single ticker; older ones
    return flat columns.
    """
    if downloaded is None or downloaded.empty:
        return pd.Series(dtype=float)
    close = downloaded["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna().sort_index()


def reaction_from_prices(prices: pd.Series, filing_date) -> dict:
    """Returns and annualised volatility after a filing.

    The base price is the first close on or after the filing date; ``return_Nd`` is the change N trading days later.
    ``volatility_20d`` is the annualised standard deviation of daily log returns over the next 20 trading days.
    Anything that cannot be computed is None.
    """
    if prices is None or len(prices) == 0:
        return dict(NO_REACTION)
    filing_dt = pd.Timestamp(filing_date)
    if prices.index.tz is not None:
        filing_dt = filing_dt.tz_localize(prices.index.tz)
    idx = int(prices.index.searchsorted(filing_dt))
    if idx >= len(prices):
        return dict(NO_REACTION)

    base = float(prices.iloc[idx])

    def ret(offset: int):
        target = idx + offset
        return float(prices.iloc[target] / base - 1) if target < len(prices) else None

    window = prices.iloc[idx : idx + 21]
    vol = None
    if len(window) >= 3:
        logret = np.log(window / window.shift(1)).dropna()
        std = logret.std()
        if not math.isnan(std):
            vol = float(std * np.sqrt(252))
    return {"return_1d": ret(1), "return_5d": ret(5), "return_20d": ret(20), "volatility_20d": vol}
