"""
CLI entry point for the preparatory stock screener.

Usage:
    python main.py AAPL MSFT NVDA
    python main.py --verbose TSLA AMZN
    python main.py --json AAPL | python -m json.tool
    python main.py --agent AAPL MSFT      # uses Claude to run and explain steps
"""
import argparse
import json
import sys

from screener.orchestrator import screen_multiple


def _verdict_line(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def print_result(result: dict, verbose: bool = False) -> None:
    symbol = result["symbol"]
    approved = result.get("approved", False)
    summary = result.get("summary", "")
    status = "APPROVED" if approved else "REJECTED"

    print(f"\n{'─'*60}")
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="5-step preparatory stock screener (from Part 2, Chapter 4)"
    )
    parser.add_argument("tickers", nargs="+", help="One or more stock ticker symbols")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detail for each step"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Output raw JSON"
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Use Claude agent to run and narrate each step (requires ANTHROPIC_API_KEY)",
    )
    args = parser.parse_args()

    if args.agent:
        from agent import screen_with_agent

        print(screen_with_agent(args.tickers))
        return

    results = screen_multiple(args.tickers)

    if args.as_json:
        print(json.dumps(results, indent=2, default=str))
        return

    for r in results:
        print_result(r, verbose=args.verbose)

    approved = [r["symbol"] for r in results if r.get("approved")]
    rejected = [r["symbol"] for r in results if not r.get("approved")]

    print(f"\n{'─'*60}")
    print(f"  SUMMARY  {len(approved)} approved / {len(rejected)} rejected")
    if approved:
        print(f"  Approved : {', '.join(approved)}")
    if rejected:
        print(f"  Rejected : {', '.join(rejected)}")
    print()


if __name__ == "__main__":
    main()
