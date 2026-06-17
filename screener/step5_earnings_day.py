"""
Step 5 — Earnings Day Outperformance vs. S&P 500.

The market's verdict on an earnings report shows up on the first trading session
after the numbers are public:

  - BMO (before market open)  → reaction is visible the SAME trading day
  - AMC (after market close)  → reaction is visible the NEXT trading day

Pass condition: stock return on reaction day > S&P 500 return on same day
"""
from typing import Any

from typing import Optional

from .data_fetcher import get_earnings_reaction_info, get_market_return_on_date, get_price_return_on_date


def run(symbol: str, earnings_info: Optional[dict] = None) -> dict[str, Any]:
    info = earnings_info if earnings_info is not None else get_earnings_reaction_info(symbol)

    if info is None:
        return _fail(
            f"Could not determine the most recent earnings announcement date for {symbol}",
            {},
        )

    announcement_date = info["announcement_date"]
    reaction_date = info["reaction_date"]
    timing = info["timing"]

    stock_ret = get_price_return_on_date(symbol, reaction_date)
    market_ret = get_market_return_on_date(reaction_date)

    if stock_ret is None or market_ret is None:
        return _fail(
            f"Price data unavailable for reaction date {reaction_date.date()} "
            f"(earnings reported {announcement_date.date()}, {timing})",
            {
                "announcement_date": str(announcement_date.date()),
                "reaction_date": str(reaction_date.date()),
                "timing": timing,
            },
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
            f"Earnings reported {announcement_date.date()} ({timing}); "
            f"reaction measured on {reaction_date.date()} — "
            f"{symbol} returned {stock_ret:+.2f}% vs S&P 500 {market_ret:+.2f}% "
            f"({'outperformed' if passed else 'underperformed'} by {abs(relative):.2f}%)"
        ),
        "data": {
            "announcement_date": str(announcement_date.date()),
            "reaction_date": str(reaction_date.date()),
            "timing": timing,
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
