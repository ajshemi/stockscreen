"""
Claude-powered stock screening agent.

Each of the 5 screening steps is exposed as a tool that Claude calls
autonomously, interprets the result, and uses to build its final verdict.

Usage:
    python agent.py AAPL MSFT NVDA
    ANTHROPIC_API_KEY=sk-... python agent.py TSLA
"""
import json
import sys

import anthropic

from screener import step1_eps_growth, step2_revenue_growth
from screener import step3_margin_expansion, step4_pe_valuation, step5_earnings_day

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "check_eps_growth",
        "description": (
            "Step 1 of the preparatory stock screen. "
            "Checks whether a stock's earnings per share (EPS) grew more than 10% "
            "year-over-year in the most recent quarter. "
            "Returns the EPS growth percentage and whether the step passed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "check_revenue_growth",
        "description": (
            "Step 2 of the preparatory stock screen. "
            "Checks whether a stock's quarterly revenue grew more than 5% year-over-year. "
            "Returns the revenue growth percentage and whether the step passed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "check_margin_expansion",
        "description": (
            "Step 3 of the preparatory stock screen. "
            "Checks whether EPS growth exceeds revenue growth, confirming that "
            "profit margins are widening. "
            "Requires the EPS growth and revenue growth values from Steps 1 and 2."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "eps_growth": {
                    "type": "number",
                    "description": "EPS growth percentage from Step 1",
                },
                "revenue_growth": {
                    "type": "number",
                    "description": "Revenue growth percentage from Step 2",
                },
            },
            "required": ["eps_growth", "revenue_growth"],
        },
    },
    {
        "name": "check_pe_valuation",
        "description": (
            "Step 4 of the preparatory stock screen. "
            "Checks whether the stock's trailing PE ratio is lower than its EPS growth rate. "
            "A PE below the growth rate suggests the stock is reasonably priced. "
            "Requires the EPS growth value from Step 1."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "eps_growth": {
                    "type": "number",
                    "description": "EPS growth percentage from Step 1",
                },
            },
            "required": ["symbol", "eps_growth"],
        },
    },
    {
        "name": "check_earnings_day_performance",
        "description": (
            "Step 5 of the preparatory stock screen. "
            "Checks whether the stock outperformed the S&P 500 on its most recent "
            "earnings announcement day. Market outperformance on earnings day signals "
            "the report positively surprised investors."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"}
            },
            "required": ["symbol"],
        },
    },
]


def _dispatch(name: str, inputs: dict) -> str:
    if name == "check_eps_growth":
        result = step1_eps_growth.run(inputs["symbol"])
    elif name == "check_revenue_growth":
        result = step2_revenue_growth.run(inputs["symbol"])
    elif name == "check_margin_expansion":
        result = step3_margin_expansion.run(
            eps_growth=inputs["eps_growth"],
            revenue_growth=inputs["revenue_growth"],
        )
    elif name == "check_pe_valuation":
        result = step4_pe_valuation.run(inputs["symbol"], inputs["eps_growth"])
    elif name == "check_earnings_day_performance":
        result = step5_earnings_day.run(inputs["symbol"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result, default=str)


SYSTEM_PROMPT = """\
You are a disciplined stock screening analyst. You apply a strict 5-step
preparatory screen to each ticker the user provides.

Rules:
1. Run the steps IN ORDER (1 → 2 → 3 → 4 → 5) for each ticker.
2. If a step FAILS, stop for that ticker and clearly state it was REJECTED.
3. Only call Step 3 after you have the EPS and revenue growth values from Steps 1 and 2.
4. Only call Step 4 after you have the EPS growth value from Step 1.
5. At the end, give a concise verdict table: APPROVED or REJECTED, and why.
"""


def screen_with_agent(symbols: list[str]) -> str:
    user_msg = (
        f"Please run the 5-step preparatory stock screen on: {', '.join(symbols)}.\n"
        "Evaluate each ticker fully before moving to the next."
    )
    messages = [{"role": "user", "content": user_msg}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = _dispatch(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            return f"Unexpected stop_reason: {response.stop_reason}"


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL"]
    print(screen_with_agent(tickers))
