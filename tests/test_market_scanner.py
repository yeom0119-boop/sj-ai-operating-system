"""Tests for the full-market scanner module."""

import unittest

from modules.market_scanner import prepare_market_universe


class MarketScannerTests(unittest.TestCase):
    """Verify preparation of ticker symbols for full-market scanning."""

    def test_prepares_unique_sorted_tickers(self) -> None:
        """Symbols are normalized, deduplicated, and sorted."""
        symbols = ["nvda", "MSFT", "NVDA", "aapl"]

        result = prepare_market_universe(symbols)

        self.assertEqual(result, ["AAPL", "MSFT", "NVDA"])

    def test_skips_invalid_symbols(self) -> None:
        """Malformed and non-string values do not stop market preparation."""
        symbols = ["NVDA", "", "BAD/TICKER", None, 123]

        result = prepare_market_universe(symbols)

        self.assertEqual(result, ["NVDA"])

    def test_empty_input_returns_empty_list(self) -> None:
        """An empty source list produces an empty market universe."""
        self.assertEqual(prepare_market_universe([]), [])


if __name__ == "__main__":
    unittest.main()