"""
Step 1 — EPS Growth > 10% (year-over-year, most recent quarter).

EPS source priority:
  1. earnings_dates.Reported EPS — adjusted/non-GAAP, aligns with the book's
     "operating income" intent, and gives 20+ quarters of depth for multi-quarter
     trend analysis.
  2. quarterly_income_stmt Basic/Diluted EPS — GAAP fallback.

quarter_idx=0  → most recent reported quarter
quarter_idx=1  → one quarter prior
quarter_idx=2  → two quarters prior
"""
from typing import Any

from .data_fetcher import get_adjusted_eps_series, get_quarterly_eps

THRESHOLD = 10.0


def run(symbol: str, quarter_idx: int = 0) -> dict[str, Any]:
    # Try adjusted (non-GAAP) EPS first for better historical depth
    eps = None
    eps_label = "Adjusted EPS"
    try:
        eps = get_adjusted_eps_series(symbol)
    except ValueError:
        pass

    if eps is None:
        try:
            eps = get_quarterly_eps(symbol)
            eps_label = "GAAP EPS"
        except ValueError as e:
            return _fail(str(e), {})

    needed = quarter_idx + 5
    if len(eps) < needed:
        return _fail(
            f"Only {len(eps)} quarters of EPS data; need {needed} for quarter_idx={quarter_idx}",
            {},
        )

    recent_date = eps.index[quarter_idx]
    prior_date  = eps.index[quarter_idx + 4]
    recent_val  = float(eps.iloc[quarter_idx])
    prior_val   = float(eps.iloc[quarter_idx + 4])

    if prior_val == 0:
        return _fail("Prior-year EPS is zero; cannot compute growth", {
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
            f"{eps_label} grew {growth:.1f}% YoY "
            f"(${prior_val:.2f} reported ~{_quarter_label(prior_date)} → "
            f"${recent_val:.2f} reported ~{_quarter_label(recent_date)}); "
            f"threshold is >{THRESHOLD}%"
        ),
        "data": {
            "quarter_end_date": str(recent_date.date()),
            "recent_quarter": str(recent_date.date()),
            "prior_quarter": str(prior_date.date()),
            "recent_eps": round(recent_val, 4),
            "prior_eps": round(prior_val, 4),
            "quarterly_eps": round(recent_val, 4),
            "eps_growth_pct": round(growth, 2),
            "eps_label": eps_label,
        },
    }


def _quarter_label(ts) -> str:
    """Convert a timestamp to a human-readable quarter label, e.g. Q1 2026."""
    month = ts.month
    year  = ts.year
    q = (month - 1) // 3 + 1
    return f"Q{q} {year}"


def _fail(reason: str, data: dict) -> dict[str, Any]:
    return {
        "step": 1,
        "name": "EPS Growth > 10%",
        "passed": False,
        "value": None,
        "threshold": THRESHOLD,
        "reason": reason,
        "data": data,
    }
