"""Prepare the U.S. stock universe for the Market Scanner."""

import csv
import re
from io import StringIO

import requests

from modules.watchlist import normalize_ticker


NASDAQ_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
)
OTHER_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
)
DIRECTORY_TIMEOUT_SECONDS = 30
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



# TODO: Add configurable liquidity and price filters.