"""
Step 5 — Earnings Day Outperformance vs. S&P 500.

On the day a company reports earnings, the market votes on whether results
surprised investors. A stock that rises more than the S&P 500 on that day
signals a positive surprise.

Pass condition: stock_return_on_earnings_day > sp500_return_on_same_day
"""
from typing import Any

from .data_fetcher import (
    get_market_return_on_date,
    get_most_recent_earnings_date,
    get_price_return_on_date,
)


def run(symbol: str) -> dict[str, Any]:
    earnings_date = get_most_recent_earnings_date(symbol)

    if earnings_date is None:
        return _fail(
            f"Could not determine the most recent earnings announcement date for {symbol}",
            {},
        )

    stock_ret = get_price_return_on_date(symbol, earnings_date)
    market_ret = get_market_return_on_date(earnings_date)

    if stock_ret is None or market_ret is None:
        return _fail(
            f"Price data unavailable for earnings date {earnings_date.date()}",
            {"earnings_date": str(earnings_date.date())},
        )

    passed = stock_ret > market_ret
    relative = round(stock_ret - market_ret, 2)

    return {
        "step": 5,
        "name": "Earnings Day Outperformance vs S&P 500",
        "passed": passed,
        "value": relative,
        "threshold": 0,
        "reason": (
            f"On {earnings_date.date()}, {symbol} returned {stock_ret:+.2f}% "
            f"vs S&P 500 {market_ret:+.2f}% "
            f"({'outperformed' if passed else 'underperformed'} by {abs(relative):.2f}%)"
        ),
        "data": {
            "earnings_date": str(earnings_date.date()),
            "stock_return_pct": round(stock_ret, 2),
            "market_return_pct": round(market_ret, 2),
            "relative_performance_pct": relative,
        },
    }


def _fail(reason: str, data: dict) -> dict[str, Any]:
    return {
        "step": 5,
        "name": "Earnings Day Outperformance vs S&P 500",
        "passed": False,
        "value": None,
        "threshold": 0,
        "reason": reason,
        "data": data,
    }
