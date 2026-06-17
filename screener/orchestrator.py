"""
Orchestrator — runs all 5 steps in sequence for one or more tickers,
optionally across the last N quarters.

screen(symbol)                 → single-quarter result (most recent)
screen_multiple(symbols)       → list of single-quarter results
screen_multi_quarter(symbol)   → per-quarter results for the last N quarters
"""
from typing import Any, Optional

from .data_fetcher import get_all_earnings_reaction_info, get_current_price
from . import (
    step1_eps_growth,
    step2_revenue_growth,
    step3_margin_expansion,
    step4_pe_valuation,
    step5_earnings_day,
)


# ── Quarter runner ────────────────────────────────────────────────────────────

def _run_quarter(
    symbol: str,
    quarter_idx: int,
    earnings_info: Optional[dict],
    stock_price: Optional[float],
) -> dict[str, Any]:
    """
    Execute all 5 steps for one quarter.

    Steps 2 & 3 may return data_unavailable=True for older quarters where
    prior-year revenue data is outside yfinance's 5-quarter window.
    In that case the orchestrator continues to steps 4 & 5 rather than failing,
    and the quarter is marked 'partial' rather than approved/rejected.

    earnings_info : pre-fetched timing dict for step 5 (AMC/BMO, reaction date).
    stock_price   : closing price on the announcement date (for step 4 PE).
    """
    result: dict[str, Any] = {
        "quarter_idx": quarter_idx,
        "steps": [],
        "approved": False,
        "partial": False,       # True when data gaps prevent a full verdict
        "summary": "",
        "quarter_end_date": None,
        "announcement_date": (
            str(earnings_info["announcement_date"].date()) if earnings_info else None
        ),
    }

    try:
        # ── Step 1: EPS Growth ────────────────────────────────────────────────
        s1 = step1_eps_growth.run(symbol, quarter_idx=quarter_idx)
        result["steps"].append(s1)
        result["quarter_end_date"] = s1["data"].get("quarter_end_date")
        if not s1["passed"]:
            result["summary"] = f"REJECTED at Step 1 — {s1['reason']}"
            return result

        eps_growth    = s1["data"]["eps_growth_pct"]
        quarterly_eps = s1["data"]["quarterly_eps"]

        # ── Step 2: Revenue Growth ────────────────────────────────────────────
        s2 = step2_revenue_growth.run(symbol, quarter_idx=quarter_idx)
        result["steps"].append(s2)
        rev_growth: Optional[float] = None

        if s2.get("data_unavailable"):
            # Data gap — record as N/A, continue to steps 4 & 5
            result["partial"] = True
        elif not s2["passed"]:
            result["summary"] = f"REJECTED at Step 2 — {s2['reason']}"
            return result
        else:
            rev_growth = s2["data"]["revenue_growth_pct"]

        # ── Step 3: Margin Expansion ──────────────────────────────────────────
        s3 = step3_margin_expansion.run(
            eps_growth=eps_growth, revenue_growth=rev_growth
        )
        result["steps"].append(s3)

        if not s3.get("data_unavailable") and not s3["passed"]:
            result["summary"] = f"REJECTED at Step 3 — {s3['reason']}"
            return result

        # ── Step 4: PE Valuation ──────────────────────────────────────────────
        s4 = step4_pe_valuation.run(
            eps_growth=eps_growth,
            quarterly_eps=quarterly_eps,
            stock_price=stock_price,
        )
        result["steps"].append(s4)
        if not s4["passed"]:
            result["summary"] = f"REJECTED at Step 4 — {s4['reason']}"
            return result

        # ── Step 5: Earnings Day Performance ─────────────────────────────────
        s5 = step5_earnings_day.run(symbol, earnings_info=earnings_info)
        result["steps"].append(s5)
        if not s5["passed"]:
            result["summary"] = f"REJECTED at Step 5 — {s5['reason']}"
            return result

        if result["partial"]:
            result["approved"] = True
            result["summary"] = (
                "APPROVED (partial) — Steps 1, 4 & 5 passed; "
                "Steps 2 & 3 skipped (revenue data unavailable for this quarter)"
            )
        else:
            result["approved"] = True
            result["summary"] = "APPROVED — passed all 5 screening criteria"

    except Exception as exc:
        result["summary"] = f"ERROR — {exc}"
        result["error"] = str(exc)

    return result


# ── Public API ────────────────────────────────────────────────────────────────

def screen(symbol: str) -> dict[str, Any]:
    """Run the 5-step screen for the most recent quarter of a single ticker."""
    symbol = symbol.upper().strip()
    all_info = get_all_earnings_reaction_info(symbol, n=1)
    earnings_info = all_info[0] if all_info else None
    stock_price = (
        earnings_info.get("stock_price_on_announcement") if earnings_info else None
    ) or get_current_price(symbol)

    result = _run_quarter(
        symbol, quarter_idx=0, earnings_info=earnings_info, stock_price=stock_price
    )
    result["symbol"] = symbol
    return result


def screen_multiple(symbols: list[str]) -> list[dict[str, Any]]:
    """Screen multiple tickers for their most recent quarter."""
    return [screen(sym) for sym in symbols]


def screen_multi_quarter(symbol: str, num_quarters: int = 3) -> dict[str, Any]:
    """
    Run the 5-step screen for each of the last `num_quarters` earnings reports
    and return one result per quarter plus a trend summary.

    EPS (Step 1) uses earnings_dates.Reported EPS which provides 20+ quarters
    of depth. Revenue (Step 2) is limited to 5 quarters by yfinance; older
    quarters show Steps 2 & 3 as N/A.
    """
    symbol = symbol.upper().strip()
    all_info = get_all_earnings_reaction_info(symbol, n=num_quarters)

    quarters: list[dict[str, Any]] = []
    for idx in range(num_quarters):
        info  = all_info[idx] if idx < len(all_info) else None
        price = info.get("stock_price_on_announcement") if info else None
        q_result = _run_quarter(
            symbol, quarter_idx=idx, earnings_info=info, stock_price=price
        )
        quarters.append(q_result)

    def _label(q: dict) -> str:
        if q["approved"] and q["partial"]:
            return "APPROVED*"
        return "APPROVED" if q["approved"] else "REJECTED"

    trend_labels   = [_label(q) for q in quarters]
    approved_count = sum(1 for q in quarters if q["approved"])

    return {
        "symbol": symbol,
        "num_quarters": num_quarters,
        "quarters": quarters,
        "approved_count": approved_count,
        "trend": " → ".join(trend_labels) + " (newest → oldest)",
        "note": "APPROVED* = Steps 2 & 3 skipped due to limited revenue history",
    }
