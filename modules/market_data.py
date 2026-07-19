"""Download stock prices and calculate core SJ technical indicators."""

from __future__ import annotations

import re

import pandas as pd
import yfinance as yf


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