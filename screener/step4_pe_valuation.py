"""
Step 4 — PE Ratio < EPS Growth Rate.

A PE ratio below the EPS growth rate means the stock is cheap relative to its
growth momentum (analogous to a PEG ratio < 1).

Pass condition: trailing_PE < eps_growth_pct
"""
from typing import Any

from .data_fetcher import get_trailing_pe


def run(symbol: str, eps_growth: float) -> dict[str, Any]:
    pe = get_trailing_pe(symbol)

    if pe is None:
        return _fail(
            "Trailing PE ratio unavailable (stock may not yet be profitable)",
            {"eps_growth_pct": eps_growth},
        )

    passed = pe < eps_growth
    peg = round(pe / eps_growth, 2) if eps_growth != 0 else None

    return {
        "step": 4,
        "name": "PE Ratio < EPS Growth %",
        "passed": passed,
        "value": round(pe, 2),
        "threshold": eps_growth,
        "reason": (
            f"Trailing PE of {pe:.1f} "
            f"{'is below' if passed else 'exceeds'} "
            f"EPS growth of {eps_growth:.1f}% "
            f"(PEG-like ratio: {peg})"
        ),
        "data": {
            "trailing_pe": round(pe, 2),
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
