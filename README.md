# SJ AI Operating System v1.2 MVP

SJ AI Operating System is a local, Markdown-based investment research system.

It downloads market data, calculates technical indicators, creates preliminary institutional-footprint scores, and stores reports in a local Obsidian-compatible vault.

## Final Goal

Build a modular decision-research platform that combines:

- Verified market data
- Company IR guidance and earnings
- Technical indicators
- Options and breadth data
- Institutional-footprint probability signals
- Multiple AI analysis engines
- Local Obsidian Markdown knowledge

## Current Working Features

- Create daily notes
- Create stock notes
- Read stock notes
- List stock notes
- Add timestamped analysis entries
- Search all Markdown notes
- List recently modified notes
- Download stock prices and volume from Yahoo Finance
- Calculate MA20, MA60, MA150, and MA200
- Calculate 20-day average volume
- Calculate OBV and RSI14
- Calculate preliminary Money In Score
- Calculate preliminary Money Out Score
- Separate confirmed facts from rule-based interpretations
- Append automated reports to Obsidian stock notes
- Preserve existing stock-note content
- Resolve U.S. stock tickers to official SEC CIK identifiers
- Collect recent official 10-K, 10-Q, and 8-K filing links

## Installation

Python 3.12 or later is recommended.

Install the required package:

```powershell

python -m pip install -r requirements.txt

```

## SEC Configuration

SEC automated access requires a local User-Agent containing a contact email.

Set it once on Windows:

```powershell
setx SEC_USER_AGENT "SJ AI Operating System your-email@example.com"
```

Replace `your-email@example.com` with your real email. Never commit personal contact information to GitHub.

## Run

From the project folder:

```powershell
python main.py
```

## Menu

1. Create daily note
2. Create stock note
3. Read stock note
4. List stock notes
5. Add stock analysis
6. Search all notes
7. List recent notes
8. Generate automated stock report
9. Generate official SEC filings report
10. Exit

## Automated Stock Report

Choose menu option 8 and enter a ticker such as:

```text
NVDA
MSFT
NOW
```

The system will:

1. Download market data
2. Calculate technical indicators
3. Calculate Money In and Money Out scores
4. Create a Markdown report
5. Append the report to `vault/Stocks/TICKER.md`

## Official SEC Filings Report

Choose menu option 9 and enter a U.S. stock ticker.

The system will:

1. Resolve the ticker to an official SEC CIK
2. Download recent SEC submission metadata
3. Filter recent 10-K, 10-Q, and 8-K filings
4. Create official SEC document links
5. Append the report to the existing Obsidian stock note

## Project Structure

```text
modules/
    __init__.py
    obsidian.py
    market_data.py
    footprint.py
    sec_filings.py

tests/
    test_main.py
    test_obsidian.py
    test_market_data.py
    test_footprint.py
    test_sec_filings.py

vault/
    Daily/
    Stocks/

main.py
requirements.txt
README.md
```

## Analysis Principles

- Current verified data comes before historical assumptions.
- Confirmed facts and hypotheses must remain separate.
- Company IR guidance and earnings are primary valuation inputs.
- SEC filing metadata is treated as a primary-source fact.
- Filing contents require separate extraction and interpretation.
- Technical indicators are probability signals, not certainty.
- Institutional-footprint scores are preliminary estimates.
- Existing Obsidian notes must never be deleted when new analysis is added.

## Current Limitations

The v1.2 system does not yet automatically:

- Extract and summarize full SEC filing contents
- Extract management guidance from earnings documents
- Collect options OI and OI changes
- Collect IV, IV Rank, and IV Percentile
- Collect put/call and gamma data
- Collect market breadth and sector flows
- Collect news from multiple verified sources
- Run cross-analysis through multiple AI engines

## Tests

Run all automated tests:

```powershell
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 25 tests
OK
```

## Data Notice

Market data is downloaded through the open-source `yfinance` package for personal research. Official filing metadata and links are collected from the U.S. SEC EDGAR API. All information requires verification before investment decisions.