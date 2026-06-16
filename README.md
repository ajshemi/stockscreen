# Stock Screener — 5-Step Preparatory Screen

Implements the stock-selection methodology from *Part 2, Chapter 4: My Preparatory Stock Screen*.

A stock must pass **all five steps** to be considered worth further investigation.

---

## The 5 Steps

| Step | Criterion | Pass condition |
|------|-----------|----------------|
| 1 | EPS Growth | Most recent quarter EPS grew **> 10%** YoY |
| 2 | Revenue Growth | Most recent quarter revenue grew **> 5%** YoY |
| 3 | Margin Expansion | EPS growth % **>** Revenue growth % |
| 4 | PE Valuation | Trailing PE **<** EPS growth % |
| 5 | Earnings Day | Stock return **>** S&P 500 return on earnings day |

---

## Project Structure

```
stockscreen/
├── screener/
│   ├── __init__.py              # Exports screen() and screen_multiple()
│   ├── data_fetcher.py          # Yahoo Finance data layer (yfinance)
│   ├── step1_eps_growth.py      # Step 1 — EPS growth > 10%
│   ├── step2_revenue_growth.py  # Step 2 — Revenue growth > 5%
│   ├── step3_margin_expansion.py# Step 3 — EPS growth > Revenue growth
│   ├── step4_pe_valuation.py    # Step 4 — PE < EPS growth %
│   ├── step5_earnings_day.py    # Step 5 — Outperformed S&P 500 on earnings day
│   └── orchestrator.py          # Chains all 5 steps; returns pass/fail per ticker
├── agent.py                     # Claude agent — runs steps as tools, narrates reasoning
├── main.py                      # CLI entry point
└── requirements.txt
```

---

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### CLI (pure Python, no API key needed)

```bash
# Screen one or more tickers
python main.py AAPL MSFT NVDA

# Show detail for every step
python main.py --verbose TSLA AMZN

# Output raw JSON
python main.py --json AAPL
```

### Claude Agent (requires `ANTHROPIC_API_KEY`)

The agent exposes each step as a tool. Claude calls them in order and explains its reasoning.

```bash
export ANTHROPIC_API_KEY=sk-...
python main.py --agent AAPL MSFT

# Or directly
python agent.py AAPL MSFT NVDA
```

---

## Example Output

```
────────────────────────────────────────────────────────────
  MSFT        [REJECTED]
  REJECTED at Step 4 — Trailing PE of 23.4 exceeds EPS growth of 23.3%

    Step 1 ✓  EPS Growth > 10%
               EPS grew 23.3% YoY ($3.47 → $4.28); threshold is >10%
    Step 2 ✓  Revenue Growth > 5%
               Revenue grew 18.3% YoY ($70.07B → $82.89B)
    Step 3 ✓  Margin Expansion
               EPS growth (23.3%) exceeds revenue growth (18.3%)
    Step 4 ✗  PE Ratio < EPS Growth %
               Trailing PE of 23.4 exceeds EPS growth of 23.3%
```

---

## Data Source

Financial data is fetched from Yahoo Finance via the [`yfinance`](https://github.com/ranaroussi/yfinance) library. No API key required for the core screener.
