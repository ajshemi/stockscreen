"""
CLI entry point for the preparatory stock screener.

Usage:
    python main.py AAPL MSFT NVDA
    python main.py --verbose TSLA AMZN
    python main.py --quarters 3 IBM               # last 3 quarters trend
    python main.py --quarters 3 --verbose IBM
    python main.py --json AAPL | python -m json.tool
    python main.py --agent AAPL MSFT              # Claude narrates each step
"""
import argparse
import json

from screener.orchestrator import screen_multi_quarter, screen_multiple

DIVIDER = "─" * 64


def print_single_result(result: dict, verbose: bool = False) -> None:
    symbol   = result["symbol"]
    approved = result.get("approved", False)
    summary  = result.get("summary", "")
    status   = "APPROVED" if approved else "REJECTED"

    print(f"\n{DIVIDER}")
    print(f"  {symbol:<10}  [{status}]")
    print(f"  {summary}")

    if verbose and result.get("steps"):
        print()
        for step in result["steps"]:
            icon = "✓" if step.get("passed") else "✗"
            print(f"    Step {step['step']} {icon}  {step['name']}")
            print(f"           {step['reason']}")

    if result.get("error"):
        print(f"  ERROR: {result['error']}")


def print_multi_quarter_result(result: dict, verbose: bool = False) -> None:
    symbol      = result["symbol"]
    num_q       = result["num_quarters"]
    approved    = result["approved_count"]
    trend       = result["trend"]

    print(f"\n{DIVIDER}")
    print(f"  {symbol} — Last {num_q} Quarters")
    print(f"  Trend: {trend}")
    print(f"  Approved: {approved}/{num_q} quarters")

    for q in result["quarters"]:
        idx            = q["quarter_idx"]
        qdate          = q.get("quarter_end_date") or "unknown date"
        ann_date       = q.get("announcement_date") or ""
        q_approved     = q.get("approved", False)
        q_summary      = q.get("summary", "")
        q_status       = "APPROVED" if q_approved else "REJECTED"

        label = f"Q{idx + 1} (reported {ann_date or qdate})"

        print(f"\n  {DIVIDER[:48]}")
        print(f"  {label}")
        print(f"  [{q_status}]  {q_summary}")

        if verbose and q.get("steps"):
            print()
            for step in q["steps"]:
                icon = "✓" if step.get("passed") else "✗"
                print(f"      Step {step['step']} {icon}  {step['name']}")
                print(f"               {step['reason']}")

        if q.get("error"):
            print(f"  ERROR: {q['error']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="5-step preparatory stock screener"
    )
    parser.add_argument("tickers", nargs="+", help="One or more stock ticker symbols")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detail for each step")
    parser.add_argument("--quarters", "-q", type=int, default=1, metavar="N",
                        help="Analyse the last N quarters (default: 1)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output raw JSON")
    parser.add_argument("--agent", action="store_true",
                        help="Use Claude agent (requires ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    if args.agent:
        from agent import screen_with_agent
        print(screen_with_agent(args.tickers))
        return

    if args.quarters > 1:
        results = [screen_multi_quarter(sym, num_quarters=args.quarters)
                   for sym in args.tickers]
        if args.as_json:
            print(json.dumps(results, indent=2, default=str))
            return
        for r in results:
            print_multi_quarter_result(r, verbose=args.verbose)
        print(f"\n{DIVIDER}")
        return

    # Single-quarter path
    results = screen_multiple(args.tickers)
    if args.as_json:
        print(json.dumps(results, indent=2, default=str))
        return
    for r in results:
        print_single_result(r, verbose=args.verbose)

    approved = [r["symbol"] for r in results if r.get("approved")]
    rejected = [r["symbol"] for r in results if not r.get("approved")]
    print(f"\n{DIVIDER}")
    print(f"  SUMMARY  {len(approved)} approved / {len(rejected)} rejected")
    if approved:
        print(f"  Approved : {', '.join(approved)}")
    if rejected:
        print(f"  Rejected : {', '.join(rejected)}")
    print()


if __name__ == "__main__":
    main()
