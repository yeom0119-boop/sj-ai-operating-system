"""Prepare the U.S. stock universe for the Market Scanner."""

import csv
from io import StringIO

from modules.watchlist import normalize_ticker


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

        symbols.append(symbol)

    return prepare_market_universe(symbols)


# TODO: Download official Nasdaq and other-exchange symbol directories.
# TODO: Add configurable liquidity and price filters.