"""
Fetches financial data from Yahoo Finance via yfinance.
All public functions return clean Python types; callers never import yfinance directly.
"""
import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol.upper())


def get_quarterly_eps(symbol: str) -> pd.Series:
    """
    Returns quarterly EPS (Basic or Diluted) as a pandas Series indexed by date,
    most-recent date first.
    """
    t = _ticker(symbol)
    stmt = t.quarterly_income_stmt
    if stmt is None or stmt.empty:
        raise ValueError(f"No quarterly income statement for {symbol}")

    for label in ("Basic EPS", "Diluted EPS"):
        if label in stmt.index:
            return stmt.loc[label].sort_index(ascending=False)

    # Fallback: Net Income / shares outstanding
    if "Net Income" in stmt.index:
        shares = t.info.get("sharesOutstanding")
        if shares and shares > 0:
            return (stmt.loc["Net Income"] / shares).sort_index(ascending=False)

    raise ValueError(f"Cannot derive EPS for {symbol}")


def get_quarterly_revenue(symbol: str) -> pd.Series:
    """Returns quarterly Total Revenue as a Series indexed by date, most-recent first."""
    t = _ticker(symbol)
    stmt = t.quarterly_income_stmt
    if stmt is None or stmt.empty:
        raise ValueError(f"No quarterly income statement for {symbol}")

    for label in ("Total Revenue", "Revenue"):
        if label in stmt.index:
            return stmt.loc[label].sort_index(ascending=False)

    raise ValueError(f"Cannot find revenue data for {symbol}")


def get_trailing_pe(symbol: str) -> Optional[float]:
    """Returns trailing twelve-month PE ratio, or None if unavailable."""
    info = _ticker(symbol).info
    pe = info.get("trailingPE")
    return float(pe) if pe else None


def get_most_recent_earnings_date(symbol: str) -> Optional[pd.Timestamp]:
    """
    Returns the most recent past earnings announcement date.
    Prefers ticker.earnings_dates; falls back to ticker.calendar.
    """
    t = _ticker(symbol)
    try:
        df = t.earnings_dates
        if df is not None and not df.empty:
            past = df[df.index.tz_localize(None) < pd.Timestamp.now()]
            if not past.empty:
                return past.index[0].tz_localize(None)
    except Exception as e:
        logger.debug("earnings_dates unavailable for %s: %s", symbol, e)

    try:
        cal = t.calendar
        if cal is not None and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if isinstance(dates, list):
                past = [d for d in dates if pd.Timestamp(d) < pd.Timestamp.now()]
                if past:
                    return pd.Timestamp(past[0])
    except Exception as e:
        logger.debug("calendar unavailable for %s: %s", symbol, e)

    return None


def get_price_return_on_date(symbol: str, date: pd.Timestamp) -> Optional[float]:
    """
    Returns the stock's percentage return on `date` vs the prior trading day.
    Looks in a ±3-day window so weekends / holidays don't break the lookup.
    """
    t = _ticker(symbol)
    start = (date - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end = (date + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    hist = t.history(start=start, end=end)
    if hist.empty:
        return None

    hist.index = hist.index.tz_localize(None)
    target_idx = hist.index.searchsorted(date)
    if target_idx == 0 or target_idx >= len(hist):
        return None

    prior_close = hist["Close"].iloc[target_idx - 1]
    day_close = hist["Close"].iloc[target_idx]
    if prior_close == 0:
        return None
    return (day_close / prior_close - 1) * 100


def get_market_return_on_date(date: pd.Timestamp) -> Optional[float]:
    """Returns S&P 500 percentage return on `date` vs the prior trading day."""
    return get_price_return_on_date("^GSPC", date)
