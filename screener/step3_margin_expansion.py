"""
Step 3 — Margin Expansion: EPS growth rate > Revenue growth rate.

If revenue_growth is None (step 2 had insufficient data), this step is marked
as data_unavailable so the orchestrator can skip it and still evaluate steps 4 & 5.
"""
from typing import Any, Optional


def run(eps_growth: float, revenue_growth: Optional[float]) -> dict[str, Any]:
    if revenue_growth is None:
        return {
            "step": 3,
            "name": "Margin Expansion (EPS growth > Revenue growth)",
            "passed": False,
            "data_unavailable": True,
            "value": None,
            "threshold": 0,
            "reason": "Skipped — revenue growth unavailable (Step 2 had insufficient data)",
            "data": {"eps_growth_pct": eps_growth, "revenue_growth_pct": None},
        }

    passed = eps_growth > revenue_growth
    spread = round(eps_growth - revenue_growth, 2)

    return {
        "step": 3,
        "name": "Margin Expansion (EPS growth > Revenue growth)",
        "passed": passed,
        "data_unavailable": False,
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
