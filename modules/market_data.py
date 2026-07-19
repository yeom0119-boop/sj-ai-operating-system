"""Download stock prices and calculate core SJ technical indicators."""

from __future__ import annotations

import re

import pandas as pd
import yfinance as yf
from modules.footprint import calculate_footprint_scores


def normalize_ticker(ticker: str) -> str:
    """Return a safe uppercase ticker symbol.

    Input:
        ticker: A user-entered stock ticker.
    Output:
        A cleaned uppercase ticker.
    Role:
        Prevent empty or unsafe ticker values from reaching the data provider.
    """
    cleaned = ticker.strip().upper()
    if not cleaned or not re.fullmatch(r"[A-Z0-9.^=-]+", cleaned):
        raise ValueError("Invalid stock ticker.")
    return cleaned


def fetch_stock_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download historical daily price and volume data.

    Input:
        ticker: A stock ticker such as NVDA or MSFT.
        period: Yahoo Finance history period.
    Output:
        A DataFrame containing daily OHLCV market data.
    Role:
        Provide verified source data for later SJ analysis.
    """
    symbol = normalize_ticker(ticker)
    data = yf.Ticker(symbol).history(period=period)

    if data.empty:
        raise RuntimeError(f"No market data found for {symbol}.")

    return data


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate MA20, MA60, OBV, and RSI14.

    Input:
        data: Historical OHLCV market data.
    Output:
        A copied DataFrame with technical-indicator columns.
    Role:
        Create the first automated SJ institutional-footprint inputs.
    """
    result = data.copy()

    result["MA20"] = result["Close"].rolling(window=20).mean()
    result["MA60"] = result["Close"].rolling(window=60).mean()
    result["MA150"] = result["Close"].rolling(window=150).mean()
    result["MA200"] = result["Close"].rolling(window=200).mean()
    result["VOLUME20"] = result["Volume"].rolling(window=20).mean()
    price_direction = result["Close"].diff().fillna(0).apply(
        lambda change: 1 if change > 0 else -1 if change < 0 else 0
    )
    result["OBV"] = (price_direction * result["Volume"]).cumsum()

    price_change = result["Close"].diff()
    gains = price_change.clip(lower=0)
    losses = -price_change.clip(upper=0)
    average_gain = gains.rolling(window=14).mean()
    average_loss = losses.rolling(window=14).mean()
    relative_strength = average_gain / average_loss
    result["RSI14"] = 100 - (100 / (1 + relative_strength))

    return result
    
def build_stock_report(ticker: str) -> str:
    """Create a Markdown market-data report for an Obsidian stock note.

    Input:
        ticker: A stock ticker such as NVDA or MSFT.
    Output:
        Markdown containing verified data and rule-based interpretations.
    Role:
        Keep confirmed market facts separate from preliminary hypotheses.
    """
    symbol = normalize_ticker(ticker)
    indicators = calculate_indicators(fetch_stock_history(symbol))
    footprint = calculate_footprint_scores(indicators)
    latest = indicators.iloc[-1]
    previous = indicators.iloc[-2]

    close_price = float(latest["Close"])
    previous_close = float(previous["Close"])
    daily_change = ((close_price / previous_close) - 1) * 100
   
    ma20 = float(latest["MA20"])
    ma60 = float(latest["MA60"])
    ma150 = float(latest["MA150"])
    ma200 = float(latest["MA200"])
    volume20 = float(latest["VOLUME20"])
    volume_ratio = (float(latest["Volume"]) / volume20) * 100
    obv = int(latest["OBV"])
    rsi14 = float(latest["RSI14"])
    market_date = latest.name.strftime("%Y-%m-%d")
    money_in_score = int(footprint["money_in_score"])
    money_out_score = int(footprint["money_out_score"])
    money_in_details = "\n".join(f"- {signal}" for signal in footprint["money_in_signals"])
    money_out_details = "\n".join(f"- {signal}" for signal in footprint["money_out_signals"])

    price_vs_ma20 = "above" if close_price >= ma20 else "below"
    price_vs_ma60 = "above" if close_price >= ma60 else "below"
    price_vs_ma150 = "above" if close_price >= ma150 else "below"
    price_vs_ma200 = "above" if close_price >= ma200 else "below"
    if rsi14 >= 70:
        rsi_state = "overbought zone"
    elif rsi14 >= 55:
        rsi_state = "positive momentum zone"
    elif rsi14 >= 50:
        rsi_state = "neutral-to-positive zone"
    elif rsi14 >= 30:
        rsi_state = "weak momentum zone"
    else:
        rsi_state = "oversold zone"

    return f"""## Automated Market Data — {market_date}
    volume_ratio = (float(latest["Volume"]) / volume20) * 100
### Confirmed facts

- Ticker: {symbol}
- Close: ${close_price:,.2f}
- Daily change: {daily_change:+.2f}%
- Volume: {int(latest["Volume"]):,}
- MA20: ${ma20:,.2f}
- MA60: ${ma60:,.2f}
- MA150: ${ma150:,.2f}
- MA200: ${ma200:,.2f}
- 20-day average volume: {int(volume20):,}
- Volume vs 20-day average: {volume_ratio:.1f}%
- OBV: {obv:,}
- RSI14: {rsi14:.2f}
- Data source: Yahoo Finance via yfinance

### Preliminary Institutional Footprint

- Money In Score: {money_in_score}/100
- Money Out Score: {money_out_score}/100

#### Money In signals

{money_in_details}

#### Money Out signals

{money_out_details}

### Rule-based interpretation

- Price is {price_vs_ma20} MA20.
- Price is {price_vs_ma60} MA60.
- Price is {price_vs_ma150} MA150.
- Price is {price_vs_ma200} MA200.
- RSI14 is in the {rsi_state}.
- This is a preliminary technical reading, not a confirmed institutional decision.
- Company IR guidance, earnings, options, breadth, and current news require separate verification.

### TODO

- Add official IR guidance and earnings data.
- Add options OI, IV, put/call, breadth, and sector-flow data.
- Calculate Money In Score and Money Out Score.
"""
