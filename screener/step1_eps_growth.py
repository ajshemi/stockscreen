"""
Step 1 — EPS Growth > 10% (year-over-year, most recent quarter).

Pass condition: (current_quarter_EPS / same_quarter_prior_year_EPS - 1) * 100 > 10
"""
from typing import Any

from .data_fetcher import get_quarterly_eps

THRESHOLD = 10.0


def run(symbol: str) -> dict[str, Any]:
    try:
        eps = get_quarterly_eps(symbol)
    except ValueError as e:
        return _fail(symbol, str(e), {})

    if len(eps) < 5:
        return _fail(
            symbol,
            f"Only {len(eps)} quarters of EPS data available; need at least 5 for YoY comparison",
            {},
        )

    recent_date, prior_date = eps.index[0], eps.index[4]
    recent_val, prior_val = float(eps.iloc[0]), float(eps.iloc[4])

    if prior_val == 0:
        return _fail(symbol, "Prior-year EPS is zero; cannot compute growth", {
            "recent_eps": recent_val,
            "prior_eps": prior_val,
        })

    growth = (recent_val / prior_val - 1) * 100
    passed = growth > THRESHOLD

    return {
        "step": 1,
        "name": "EPS Growth > 10%",
        "passed": passed,
        "value": round(growth, 2),
        "threshold": THRESHOLD,
        "reason": (
            f"EPS grew {growth:.1f}% YoY "
            f"(${prior_val:.4f} in {prior_date.date()} → ${recent_val:.4f} in {recent_date.date()}); "
            f"threshold is >{THRESHOLD}%"
        ),
        "data": {
            "recent_quarter": str(recent_date.date()),
            "prior_quarter": str(prior_date.date()),
            "recent_eps": round(recent_val, 4),
            "prior_eps": round(prior_val, 4),
            "eps_growth_pct": round(growth, 2),
        },
    }


def _fail(symbol: str, reason: str, data: dict) -> dict[str, Any]:
    return {
        "step": 1,
        "name": "EPS Growth > 10%",
        "passed": False,
        "value": None,
        "threshold": THRESHOLD,
        "reason": reason,
        "data": data,
    }
