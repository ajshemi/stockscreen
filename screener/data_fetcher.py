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


def get_adjusted_eps_series(symbol: str) -> pd.Series:
    """
    Returns quarterly adjusted (non-GAAP) EPS from earnings_dates.Reported EPS,
    indexed by announcement date (tz-naive), most-recent first.

    This matches the book's "operating income" intent and goes back 20+ quarters,
    far deeper than the 5-quarter limit of quarterly_income_stmt.
    Raises ValueError if data is unavailable.
    """
    t = _ticker(symbol)
    df = t.earnings_dates
    if df is None or df.empty:
        raise ValueError(f"No earnings_dates available for {symbol}")

    reported = df["Reported EPS"].dropna()
    past = reported[reported.index.tz_convert(None) < pd.Timestamp.now()]
    if past.empty:
        raise ValueError(f"No past Reported EPS in earnings_dates for {symbol}")

    result = past.sort_index(ascending=False)
    result.index = result.index.tz_convert(None)
    return result


def get_current_price(symbol: str) -> Optional[float]:
    """Returns the current stock price."""
    info = _ticker(symbol).info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    return float(price) if price else None


def get_close_price(symbol: str, date: pd.Timestamp) -> Optional[float]:
    """Returns the closing price on the trading day on or immediately before `date`."""
    t = _ticker(symbol)
    start = (date - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end = (date + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    hist = t.history(start=start, end=end)
    if hist.empty:
        return None
    hist.index = hist.index.tz_localize(None)
    idx = hist.index.searchsorted(date, side="right") - 1
    if idx < 0:
        return None
    return float(hist["Close"].iloc[idx])


def get_earnings_reaction_info(symbol: str) -> Optional[dict]:
    """
    Returns timing information for the most recent earnings announcement so that
    step 5 can evaluate the correct trading day's reaction.

    Returned dict keys:
        announcement_date : pd.Timestamp  — when earnings were reported (tz-naive)
        reaction_date     : pd.Timestamp  — trading day to measure market reaction
        timing            : str           — 'AMC', 'BMO', or 'unknown (assumed AMC)'

    Logic:
        - AMC (after market close, timestamp hour >= 12): reaction shows on the
          NEXT trading day because the market was already closed.
        - BMO (before market open, timestamp hour < 12): reaction shows on the
          SAME trading day after the open.
        - Unknown timing: default to next trading day (AMC is more common for
          large-cap US companies).

    get_price_return_on_date() uses searchsorted over actual trading days, so
    passing a weekend or holiday as reaction_date automatically resolves to the
    following Monday / next trading session.
    """
    t = _ticker(symbol)

    # ── Primary: earnings_dates (requires lxml) ───────────────────────────────
    try:
        df = t.earnings_dates
        if df is not None and not df.empty:
            naive_idx = df.index.tz_convert(None)
            past = df[naive_idx < pd.Timestamp.now()]
            if not past.empty:
                ts = past.index[0]                      # tz-aware timestamp
                announcement_date = ts.tz_convert(None) # strip tz, keep local time
                hour = ts.hour                          # hour in exchange local time

                if hour >= 12:
                    # After market close — reaction is next trading day
                    reaction_date = announcement_date + pd.Timedelta(days=1)
                    timing = "AMC"
                else:
                    # Before market open — reaction is same trading day
                    reaction_date = announcement_date
                    timing = "BMO"

                return {
                    "announcement_date": announcement_date,
                    "reaction_date": reaction_date,
                    "timing": timing,
                }
    except Exception as e:
        logger.debug("earnings_dates unavailable for %s: %s", symbol, e)

    # ── Fallback: calendar (no timing info) ──────────────────────────────────
    try:
        cal = t.calendar
        if cal is not None and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if isinstance(dates, list):
                past = [d for d in dates if pd.Timestamp(d) < pd.Timestamp.now()]
                if past:
                    announcement_date = pd.Timestamp(past[0])
                    return {
                        "announcement_date": announcement_date,
                        "reaction_date": announcement_date + pd.Timedelta(days=1),
                        "timing": "unknown (assumed AMC)",
                    }
    except Exception as e:
        logger.debug("calendar unavailable for %s: %s", symbol, e)

    # ── Last resort: most recent income-statement quarter-end date ────────────
    try:
        stmt = t.quarterly_income_stmt
        if stmt is not None and not stmt.empty:
            most_recent = pd.Timestamp(stmt.columns.max())
            if most_recent < pd.Timestamp.now():
                return {
                    "announcement_date": most_recent,
                    "reaction_date": most_recent + pd.Timedelta(days=1),
                    "timing": "unknown (assumed AMC)",
                }
    except Exception as e:
        logger.debug("income statement fallback failed for %s: %s", symbol, e)

    return None


def get_all_earnings_reaction_info(symbol: str, n: int = 4) -> list[dict]:
    """
    Returns timing info for the `n` most recent past earnings announcements,
    most-recent first. Each dict contains:
        announcement_date         : pd.Timestamp  — when reported (tz-naive)
        reaction_date             : pd.Timestamp  — trading day to measure reaction
        timing                    : str           — 'AMC', 'BMO', or 'unknown (assumed AMC)'
        stock_price_on_announcement: float | None — close price on announcement_date
          (for AMC this is the pre-announcement close; for BMO the same-day close)

    Used by the multi-quarter orchestrator so step 4 can compute a historically
    accurate PE instead of relying on today's trailing PE.
    """
    t = _ticker(symbol)
    results: list[dict] = []

    try:
        df = t.earnings_dates
        if df is not None and not df.empty:
            naive_idx = df.index.tz_convert(None)
            past = df[naive_idx < pd.Timestamp.now()]
            for ts in past.index[:n]:
                announcement_date = ts.tz_convert(None)
                hour = ts.hour
                if hour >= 12:
                    reaction_date = announcement_date + pd.Timedelta(days=1)
                    timing = "AMC"
                else:
                    reaction_date = announcement_date
                    timing = "BMO"
                results.append({
                    "announcement_date": announcement_date,
                    "reaction_date": reaction_date,
                    "timing": timing,
                    "stock_price_on_announcement": get_close_price(symbol, announcement_date),
                })
            if results:
                return results
    except Exception as e:
        logger.debug("earnings_dates unavailable for %s: %s", symbol, e)

    # Fallback: derive dates from income statement quarter-end dates (no timing info)
    try:
        stmt = t.quarterly_income_stmt
        if stmt is not None and not stmt.empty:
            past_cols = [c for c in stmt.columns if pd.Timestamp(c) < pd.Timestamp.now()]
            for col in sorted(past_cols, reverse=True)[:n]:
                announcement_date = pd.Timestamp(col)
                reaction_date = announcement_date + pd.Timedelta(days=1)
                results.append({
                    "announcement_date": announcement_date,
                    "reaction_date": reaction_date,
                    "timing": "unknown (assumed AMC)",
                    "stock_price_on_announcement": get_close_price(symbol, announcement_date),
                })
    except Exception as e:
        logger.debug("income statement fallback failed for %s: %s", symbol, e)

    return results


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
