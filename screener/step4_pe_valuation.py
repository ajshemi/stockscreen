"""
Step 4 — PE Ratio < EPS Growth Rate.

PE is computed as: stock_price / (4 × quarterly_eps)
Using 4× a single quarter's EPS annualises it, matching the book's method.

For the most recent quarter the orchestrator passes the current stock price.
For historical quarters it passes the closing price on the earnings announcement
date, giving a historically accurate "PE at the time of the report."

Pass condition: computed_pe < eps_growth_pct
"""
from typing import Any, Optional


def run(
    eps_growth: float,
    quarterly_eps: float,
    stock_price: Optional[float],
) -> dict[str, Any]:

    if stock_price is None or stock_price <= 0:
        return _fail(
            "Stock price unavailable; cannot compute PE",
            {"eps_growth_pct": eps_growth},
        )

    if quarterly_eps <= 0:
        return _fail(
            f"Quarterly EPS is {quarterly_eps:.4f} (non-positive); PE undefined",
            {"eps_growth_pct": eps_growth, "quarterly_eps": quarterly_eps},
        )

    annualised_eps = quarterly_eps * 4
    pe = stock_price / annualised_eps
    passed = pe < eps_growth
    peg = round(pe / eps_growth, 2) if eps_growth != 0 else None

    return {
        "step": 4,
        "name": "PE Ratio < EPS Growth %",
        "passed": passed,
        "value": round(pe, 2),
        "threshold": eps_growth,
        "reason": (
            f"PE of {pe:.1f} (${stock_price:.2f} / 4×${quarterly_eps:.4f}) "
            f"{'is below' if passed else 'exceeds'} "
            f"EPS growth of {eps_growth:.1f}% "
            f"(PEG-like ratio: {peg})"
        ),
        "data": {
            "stock_price": round(stock_price, 2),
            "quarterly_eps": round(quarterly_eps, 4),
            "annualised_eps": round(annualised_eps, 4),
            "computed_pe": round(pe, 2),
            "eps_growth_pct": eps_growth,
            "peg_ratio": peg,
        },
    }


def _fail(reason: str, data: dict) -> dict[str, Any]:
    return {
        "step": 4,
        "name": "PE Ratio < EPS Growth %",
        "passed": False,
        "value": None,
        "threshold": None,
        "reason": reason,
        "data": data,
    }
