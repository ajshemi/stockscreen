"""
Orchestrator — runs all 5 steps in sequence for one or more ticker symbols.

Steps are run in order; a failure at any step records the reason and stops
evaluation for that ticker (the remaining steps are skipped since they depend
on earlier data).
"""
from typing import Any

from . import (
    step1_eps_growth,
    step2_revenue_growth,
    step3_margin_expansion,
    step4_pe_valuation,
    step5_earnings_day,
)


def screen(symbol: str) -> dict[str, Any]:
    """Run the 5-step screen for a single ticker. Always returns a result dict."""
    symbol = symbol.upper().strip()
    result: dict[str, Any] = {
        "symbol": symbol,
        "steps": [],
        "approved": False,
        "summary": "",
    }

    try:
        # ── Step 1: EPS Growth ────────────────────────────────────────────────
        s1 = step1_eps_growth.run(symbol)
        result["steps"].append(s1)
        if not s1["passed"]:
            result["summary"] = f"REJECTED at Step 1 — {s1['reason']}"
            return result

        eps_growth = s1["data"]["eps_growth_pct"]

        # ── Step 2: Revenue Growth ────────────────────────────────────────────
        s2 = step2_revenue_growth.run(symbol)
        result["steps"].append(s2)
        if not s2["passed"]:
            result["summary"] = f"REJECTED at Step 2 — {s2['reason']}"
            return result

        rev_growth = s2["data"]["revenue_growth_pct"]

        # ── Step 3: Margin Expansion ──────────────────────────────────────────
        s3 = step3_margin_expansion.run(eps_growth=eps_growth, revenue_growth=rev_growth)
        result["steps"].append(s3)
        if not s3["passed"]:
            result["summary"] = f"REJECTED at Step 3 — {s3['reason']}"
            return result

        # ── Step 4: PE vs EPS Growth ──────────────────────────────────────────
        s4 = step4_pe_valuation.run(symbol, eps_growth=eps_growth)
        result["steps"].append(s4)
        if not s4["passed"]:
            result["summary"] = f"REJECTED at Step 4 — {s4['reason']}"
            return result

        # ── Step 5: Earnings Day Performance ─────────────────────────────────
        s5 = step5_earnings_day.run(symbol)
        result["steps"].append(s5)
        if not s5["passed"]:
            result["summary"] = f"REJECTED at Step 5 — {s5['reason']}"
            return result

        result["approved"] = True
        result["summary"] = f"APPROVED — {symbol} passed all 5 screening criteria"

    except Exception as exc:
        result["summary"] = f"ERROR screening {symbol}: {exc}"
        result["error"] = str(exc)

    return result


def screen_multiple(symbols: list[str]) -> list[dict[str, Any]]:
    """Screen a list of tickers and return one result dict per symbol."""
    return [screen(sym) for sym in symbols]
