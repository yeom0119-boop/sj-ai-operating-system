"""Tests for the full-market scanner module."""

import unittest

from modules.market_scanner import (
    parse_symbol_directory,
    prepare_market_universe,
)


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

    def test_parses_stocks_and_excludes_etfs_and_test_issues(self) -> None:
        """Official directory parsing keeps stocks and removes excluded rows."""
        directory_text = (
            "Symbol|Security Name|Test Issue|ETF\n"
            "NVDA|NVIDIA Corporation|N|N\n"
            "QQQ|Invesco QQQ Trust|N|Y\n"
            "ZTEST|Nasdaq Test Stock|Y|N\n"
            "File Creation Time: 07232026||||\n"
        )

        result = parse_symbol_directory(directory_text, "Symbol")

        self.assertEqual(result, ["NVDA"])

    def test_rejects_directory_without_symbol_column(self) -> None:
        """A provider format change raises a clear error."""
        directory_text = "Wrong Column|Test Issue|ETF\nNVDA|N|N\n"

        with self.assertRaisesRegex(
            ValueError,
            "symbol directory is missing column: Symbol",
        ):
            parse_symbol_directory(directory_text, "Symbol")


if __name__ == "__main__":
    unittest.main()