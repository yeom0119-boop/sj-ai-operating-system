"""Prepare the U.S. stock universe for the Market Scanner."""

import csv
import re
from io import StringIO

import requests
import yfinance as yf

from modules.watchlist import normalize_ticker


NASDAQ_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
)
OTHER_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
)
DIRECTORY_TIMEOUT_SECONDS = 30
MARKET_DATA_BATCH_SIZE = 100
MARKET_DATA_PERIOD = "1mo"
EXCLUDED_SECURITY_PATTERN = re.compile(
    r"\b("
    r"warrants?|"
    r"rights?|"
    r"units?|"
    r"preferred stock|"
    r"preferred shares?|"
    r"senior notes?|"
    r"notes due|"
    r"debentures?"
    r")\b",
    re.IGNORECASE,
)


def is_supported_stock(security_name: str) -> bool:
    """Return whether a security description represents a supported stock.

    Input: official security name from an exchange directory.
    Output: True for supported stocks and False for excluded security types.
    Role: remove warrants, rights, units, preferred shares, and debt securities.
    """
    return EXCLUDED_SECURITY_PATTERN.search(security_name) is None

def prepare_market_universe(symbols: list[str]) -> list[str]:
    """Return unique, validated ticker symbols for market scanning.

    Input: raw ticker symbols collected from a market-listing source.
    Output: sorted list of unique and valid ticker symbols.
    Role: clean the full-market symbol list before data collection and filtering.
    """
    valid_symbols = []

    for symbol in symbols:
        if not isinstance(symbol, str):
            continue

        try:
            valid_symbols.append(normalize_ticker(symbol))
        except ValueError:
            # Skip malformed symbols without stopping the full-market scan.
            continue

    return sorted(set(valid_symbols))


def parse_symbol_directory(
    directory_text: str,
    symbol_column: str,
) -> list[str]:
    """Extract tradable stock symbols from a Nasdaq directory file.

    Input: pipe-delimited directory text and the name of its symbol column.
    Output: sorted list of valid non-test, non-ETF ticker symbols.
    Role: convert official exchange directory data into scanner-ready symbols.
    """
    reader = csv.DictReader(StringIO(directory_text), delimiter="|")

    if not reader.fieldnames or symbol_column not in reader.fieldnames:
        raise ValueError(f"symbol directory is missing column: {symbol_column}")

    symbols = []

    for row in reader:
        symbol = (row.get(symbol_column) or "").strip()

        if not symbol or symbol == "File Creation Time":
            continue

        if (row.get("Test Issue") or "").strip().upper() == "Y":
            continue

        if (row.get("ETF") or "").strip().upper() == "Y":
            continue

        security_name = (row.get("Security Name") or "").strip()
        if not is_supported_stock(security_name):
            continue

        symbols.append(symbol)        

    return prepare_market_universe(symbols)


def download_symbol_directory(url: str) -> str:
    """Download one official market symbol directory.

    Input: official Nasdaq Trader directory URL.
    Output: downloaded pipe-delimited text.
    Role: retrieve the latest exchange-listed symbols with a fixed timeout.
    """
    response = requests.get(
        url,
        timeout=DIRECTORY_TIMEOUT_SECONDS,
        headers={"User-Agent": "SJ AI Operating System/2.0"},
    )
    response.raise_for_status()
    return response.text


def collect_us_market_universe() -> list[str]:
    """Collect the current U.S. market stock universe.

    Input: latest Nasdaq and other-exchange directory files.
    Output: combined, unique, sorted list of non-ETF ticker symbols.
    Role: provide full-market candidates for the scanner filtering stage.
    """
    nasdaq_text = download_symbol_directory(NASDAQ_LISTED_URL)
    other_text = download_symbol_directory(OTHER_LISTED_URL)

    nasdaq_symbols = parse_symbol_directory(nasdaq_text, "Symbol")
    other_symbols = parse_symbol_directory(other_text, "ACT Symbol")

    return prepare_market_universe(nasdaq_symbols + other_symbols)

def collect_market_rows(
    tickers: list[str],
    batch_size: int = MARKET_DATA_BATCH_SIZE,
) -> list[dict[str, object]]:
    """Collect latest price and average volume in manageable batches.

    Input: market ticker symbols and the number downloaded per request.
    Output: normalized rows containing ticker, price, and average volume.
    Role: prepare full-market liquidity data before candidate filtering.
    """
    if batch_size <= 0:
        raise ValueError("market data batch size must be positive")

    normalized_tickers = prepare_market_universe(tickers)
    market_rows = []

    for start in range(0, len(normalized_tickers), batch_size):
        ticker_batch = normalized_tickers[start : start + batch_size]
        provider_tickers = [
            ticker.replace(".", "-")
            for ticker in ticker_batch
        ]

        try:
            history = yf.download(
                provider_tickers,
                period=MARKET_DATA_PERIOD,
                interval="1d",
                group_by="column",
                auto_adjust=False,
                progress=False,
                threads=True,
                timeout=DIRECTORY_TIMEOUT_SECONDS,
            )
        except Exception:
            # Skip one failed provider batch and continue the full scan.
            continue

        if history.empty:
            continue

        has_multiple_column_levels = (
            getattr(history.columns, "nlevels", 1) > 1
        )

        for ticker, provider_ticker in zip(
            ticker_batch,
            provider_tickers,
        ):
            try:
                if has_multiple_column_levels:
                    close_values = history[("Close", provider_ticker)]
                    volume_values = history[("Volume", provider_ticker)]
                else:
                    close_values = history["Close"]
                    volume_values = history["Volume"]

                valid_close_values = close_values.dropna()
                valid_volume_values = volume_values.dropna()

                if valid_close_values.empty or valid_volume_values.empty:
                    continue

                price = float(valid_close_values.iloc[-1])
                average_volume = float(valid_volume_values.mean())
            except (KeyError, TypeError, ValueError):
                # One unavailable ticker must not stop the full-market scan.
                continue

            market_rows.append(
                {
                    "ticker": ticker,
                    "price": round(price, 2),
                    "average_volume": round(average_volume),
                }
            )

    return sorted(market_rows, key=lambda row: row["ticker"])
def filter_market_candidates(
    market_rows: list[dict[str, object]],
    min_price: float,
    min_average_volume: int,
    min_average_dollar_volume: float,
) -> list[dict[str, object]]:
    """Filter the market universe by price and trading liquidity.

    Input: ticker market rows and configurable minimum thresholds.
    Output: sorted candidate rows that satisfy every threshold.
    Role: reduce the full market before expensive deep analysis.
    """
    if (
        min_price < 0
        or min_average_volume < 0
        or min_average_dollar_volume < 0
    ):
        raise ValueError("scanner thresholds cannot be negative")

    candidates = []

    for row in market_rows:
        try:
            ticker = normalize_ticker(str(row["ticker"]))
            price = float(row["price"])
            average_volume = float(row["average_volume"])
        except (KeyError, TypeError, ValueError):
            # Skip incomplete provider rows without stopping the full scan.
            continue

        if price < 0 or average_volume < 0:
            continue

        average_dollar_volume = price * average_volume

        if price < min_price:
            continue

        if average_volume < min_average_volume:
            continue

        if average_dollar_volume < min_average_dollar_volume:
            continue

        candidates.append(
            {
                "ticker": ticker,
                "price": round(price, 2),
                "average_volume": round(average_volume),
                "average_dollar_volume": round(
                    average_dollar_volume,
                    2,
                ),
            }
        )

    return sorted(candidates, key=lambda candidate: candidate["ticker"])


# TODO: Add configurable liquidity and price filters.