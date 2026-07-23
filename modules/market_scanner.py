"""Prepare the U.S. stock universe for the Market Scanner."""

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


# TODO: Collect official U.S. exchange symbol lists.
# TODO: Add configurable liquidity and price filters.