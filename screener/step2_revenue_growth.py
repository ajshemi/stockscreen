"""
Step 2 — Revenue Growth > 5% (year-over-year, most recent quarter).

Revenue data comes from quarterly_income_stmt, which yfinance caps at 5 quarters.
YoY comparison needs the quarter from one year ago (index + 4), so:
  - quarter_idx=0 : full data available (0 vs 4, both in the 5-quarter window)
  - quarter_idx=1+ : prior-year quarter falls outside the window → data_unavailable=True

When data_unavailable=True the orchestrator skips steps 2 & 3 rather than hard-
failing, so steps 1, 4, and 5 can still be evaluated for trend analysis.
"""
from typing import Any

from .data_fetcher import get_quarterly_revenue

THRESHOLD = 5.0


def run(symbol: str, quarter_idx: int = 0) -> dict[str, Any]:
    try:
        rev = get_quarterly_revenue(symbol)
    except ValueError as e:
        return _unavailable(str(e))

    needed = quarter_idx + 5
    if len(rev) < needed:
        return _unavailable(
            f"Prior-year revenue unavailable: only {len(rev)} quarters in yfinance "
            f"(need {needed} for quarter_idx={quarter_idx}). "
            f"Steps 2 & 3 are skipped for this quarter."
        )

    recent_date = rev.index[quarter_idx]
    prior_date  = rev.index[quarter_idx + 4]
    recent_val  = float(rev.iloc[quarter_idx])
    prior_val   = float(rev.iloc[quarter_idx + 4])

    if prior_val == 0:
        return _unavailable("Prior-year revenue is zero; cannot compute growth")

    growth = (recent_val / prior_val - 1) * 100
    passed = growth > THRESHOLD

    return {
        "step": 2,
        "name": "Revenue Growth > 5%",
        "passed": passed,
        "data_unavailable": False,
        "value": round(growth, 2),
        "threshold": THRESHOLD,
        "reason": (
            f"Revenue grew {growth:.1f}% YoY "
            f"({_fmt(prior_val)} in {prior_date.date()} → "
            f"{_fmt(recent_val)} in {recent_date.date()}); "
            f"threshold is >{THRESHOLD}%"
        ),
        "data": {
            "quarter_end_date": str(recent_date.date()),
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


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "step": 2,
        "name": "Revenue Growth > 5%",
        "passed": False,
        "data_unavailable": True,
        "value": None,
        "threshold": THRESHOLD,
        "reason": reason,
        "data": {},
    }
