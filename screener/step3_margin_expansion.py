"""
Step 3 — Margin Expansion: EPS growth rate > Revenue growth rate.

A faster-growing EPS than revenue means the company is earning more per dollar
of sales — i.e., profit margins are widening.

Pass condition: eps_growth_pct > revenue_growth_pct
"""
from typing import Any


def run(eps_growth: float, revenue_growth: float) -> dict[str, Any]:
    passed = eps_growth > revenue_growth
    spread = round(eps_growth - revenue_growth, 2)

    return {
        "step": 3,
        "name": "Margin Expansion (EPS growth > Revenue growth)",
        "passed": passed,
        "value": spread,
        "threshold": 0,
        "reason": (
            f"EPS growth ({eps_growth:.1f}%) "
            f"{'exceeds' if passed else 'does not exceed'} "
            f"revenue growth ({revenue_growth:.1f}%); "
            f"margin spread is {spread:+.1f}pp"
        ),
        "data": {
            "eps_growth_pct": eps_growth,
            "revenue_growth_pct": revenue_growth,
            "margin_spread_pp": spread,
        },
    }
