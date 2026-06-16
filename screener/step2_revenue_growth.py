"""
Step 2 — Revenue Growth > 5% (year-over-year, most recent quarter).

Pass condition: (current_quarter_revenue / same_quarter_prior_year_revenue - 1) * 100 > 5
"""
from typing import Any

from .data_fetcher import get_quarterly_revenue

THRESHOLD = 5.0


def run(symbol: str) -> dict[str, Any]:
    try:
        rev = get_quarterly_revenue(symbol)
    except ValueError as e:
        return _fail(symbol, str(e), {})

    if len(rev) < 5:
        return _fail(
            symbol,
            f"Only {len(rev)} quarters of revenue data available; need at least 5 for YoY comparison",
            {},
        )

    recent_date, prior_date = rev.index[0], rev.index[4]
    recent_val, prior_val = float(rev.iloc[0]), float(rev.iloc[4])

    if prior_val == 0:
        return _fail(symbol, "Prior-year revenue is zero; cannot compute growth", {})

    growth = (recent_val / prior_val - 1) * 100
    passed = growth > THRESHOLD

    return {
        "step": 2,
        "name": "Revenue Growth > 5%",
        "passed": passed,
        "value": round(growth, 2),
        "threshold": THRESHOLD,
        "reason": (
            f"Revenue grew {growth:.1f}% YoY "
            f"({_fmt(prior_val)} in {prior_date.date()} → {_fmt(recent_val)} in {recent_date.date()}); "
            f"threshold is >{THRESHOLD}%"
        ),
        "data": {
            "recent_quarter": str(recent_date.date()),
            "prior_quarter": str(prior_date.date()),
            "recent_revenue": float(recent_val),
            "prior_revenue": float(prior_val),
            "revenue_growth_pct": round(growth, 2),
        },
    }


def _fmt(val: float) -> str:
    if abs(val) >= 1e12:
        return f"${val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.2f}M"
    return f"${val:,.0f}"


def _fail(symbol: str, reason: str, data: dict) -> dict[str, Any]:
    return {
        "step": 2,
        "name": "Revenue Growth > 5%",
        "passed": False,
        "value": None,
        "threshold": THRESHOLD,
        "reason": reason,
        "data": data,
    }
