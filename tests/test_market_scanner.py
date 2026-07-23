"""Tests for the full-market scanner module."""

import unittest
from unittest.mock import Mock, patch
from modules.market_scanner import (
    DIRECTORY_TIMEOUT_SECONDS,
    NASDAQ_LISTED_URL,
    collect_us_market_universe,
    download_symbol_directory,
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


    def test_downloads_symbol_directory_with_timeout(self) -> None:
        """Official directory requests use a timeout and return text."""
        response = Mock()
        response.text = "Symbol|Security Name\nNVDA|NVIDIA Corporation\n"

        with patch(
            "modules.market_scanner.requests.get",
            return_value=response,
        ) as request_get:
            result = download_symbol_directory(NASDAQ_LISTED_URL)

        self.assertEqual(result, response.text)
        request_get.assert_called_once_with(
            NASDAQ_LISTED_URL,
            timeout=DIRECTORY_TIMEOUT_SECONDS,
            headers={"User-Agent": "SJ AI Operating System/2.0"},
        )
        response.raise_for_status.assert_called_once_with()

    def test_collects_and_combines_exchange_directories(self) -> None:
        """Nasdaq and other-exchange symbols become one unique universe."""
        nasdaq_text = (
            "Symbol|Security Name|Test Issue|ETF\n"
            "NVDA|NVIDIA Corporation|N|N\n"
            "QQQ|Invesco QQQ Trust|N|Y\n"
        )
        other_text = (
            "ACT Symbol|Security Name|Test Issue|ETF\n"
            "MSFT|Microsoft Corporation|N|N\n"
            "NVDA|NVIDIA Corporation|N|N\n"
        )

        with patch(
            "modules.market_scanner.download_symbol_directory",
            side_effect=[nasdaq_text, other_text],
        ) as downloader:
            result = collect_us_market_universe()

        self.assertEqual(result, ["MSFT", "NVDA"])
        self.assertEqual(downloader.call_count, 2)


if __name__ == "__main__":
    unittest.main()