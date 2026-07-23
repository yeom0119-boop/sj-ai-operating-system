"""Tests for the full-market scanner module."""

import unittest
from unittest.mock import Mock, patch

import pandas as pd
from modules.market_scanner import (
    DIRECTORY_TIMEOUT_SECONDS,
    NASDAQ_LISTED_URL,
    build_technical_snapshot,
    collect_market_rows,
    collect_technical_rows,
    collect_us_market_universe,
    download_symbol_directory,
    filter_market_candidates,
    filter_technical_candidates,
    is_supported_stock,
    parse_symbol_directory,
    scan_us_market,
    scan_us_market_technical_candidates,
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

    def test_identifies_supported_and_excluded_security_types(self) -> None:
        """Common stocks and ADRs remain while unsupported securities leave."""
        supported_names = [
            "NVIDIA Corporation - Common Stock",
            "Alibaba Group Holding Limited - American Depositary Shares",
            "Berkshire Hathaway Inc. - Class B Common Stock",
        ]
        excluded_names = [
            "Example Acquisition Corp. - Warrants",
            "Example Acquisition Corp. - Units",
            "Example Acquisition Corp. - Rights",
            "Example Corporation - Preferred Stock",
            "Example Corporation - Senior Notes due 2030",
        ]

        for security_name in supported_names:
            with self.subTest(security_name=security_name):
                self.assertTrue(is_supported_stock(security_name))

        for security_name in excluded_names:
            with self.subTest(security_name=security_name):
                self.assertFalse(is_supported_stock(security_name))
    def test_skips_incomplete_technical_history(self) -> None:
        """Insufficient history does not produce unreliable MA200 data."""
        close_values = pd.Series(
            range(1, 101),
            dtype="float64",
        )
        history = pd.DataFrame(
            {
                "Close": close_values,
                "High": close_values + 1.0,
                "Low": close_values - 1.0,
                "Volume": 1_000_000,
            }
        )

        result = build_technical_snapshot("NVDA", history)

        self.assertIsNone(result)

    def test_builds_latest_technical_snapshot(self) -> None:
        """Historical OHLCV data becomes one latest technical snapshot."""
        close_values = pd.Series(
            range(1, 221),
            dtype="float64",
        )
        history = pd.DataFrame(
            {
                "Close": close_values,
                "High": close_values + 1.0,
                "Low": close_values - 1.0,
                "Volume": 1_000_000,
            }
        )

        result = build_technical_snapshot("nvda", history)

        self.assertEqual(
            result,
            {
                "ticker": "NVDA",
                "price": 220.0,
                "ma20": 210.5,
                "ma60": 190.5,
                "ma150": 145.5,
                "ma200": 120.5,
                "average_volume_20": 1_000_000,
                "obv": 219_000_000.0,
                "obv_change_20": 20_000_000.0,
                "ad": 0.0,
                "ad_change_20": 0.0,
                "rsi14": 100.0,
            },
        )
    def test_collects_technical_rows_for_liquid_candidates(self) -> None:
        """Only supplied liquid candidates receive technical snapshots."""
        close_values = pd.Series(
            range(1, 221),
            dtype="float64",
        )
        columns = pd.MultiIndex.from_tuples(
            [
                ("Close", "NVDA"),
                ("High", "NVDA"),
                ("Low", "NVDA"),
                ("Volume", "NVDA"),
            ]
        )
        history = pd.DataFrame(
            {
                columns[0]: close_values,
                columns[1]: close_values + 1.0,
                columns[2]: close_values - 1.0,
                columns[3]: 1_000_000,
            }
        )
        candidates = [
            {
                "ticker": "NVDA",
                "price": 220.0,
                "average_volume": 1_000_000,
                "average_dollar_volume": 220_000_000.0,
            }
        ]

        with patch(
            "modules.market_scanner.yf.download",
            return_value=history,
        ) as downloader:
            result = collect_technical_rows(candidates)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ticker"], "NVDA")
        self.assertEqual(result[0]["price"], 220.0)
        self.assertEqual(result[0]["ma200"], 120.5)
        self.assertEqual(result[0]["rsi14"], 100.0)
        downloader.assert_called_once()
    def test_filters_candidates_by_technical_rules(self) -> None:
        """Only stocks satisfying every enabled technical rule remain."""
        technical_rows = [
            {
                "ticker": "PASS",
                "price": 110.0,
                "ma20": 100.0,
                "rsi14": 60.0,
                "obv_change_20": 5_000_000.0,
                "ad_change_20": 2_000_000.0,
            },
            {
                "ticker": "LOWRSI",
                "price": 110.0,
                "ma20": 100.0,
                "rsi14": 45.0,
                "obv_change_20": 5_000_000.0,
                "ad_change_20": 2_000_000.0,
            },
            {
                "ticker": "BELOWMA",
                "price": 95.0,
                "ma20": 100.0,
                "rsi14": 60.0,
                "obv_change_20": 5_000_000.0,
                "ad_change_20": 2_000_000.0,
            },
            {
                "ticker": "FALLOBV",
                "price": 110.0,
                "ma20": 100.0,
                "rsi14": 60.0,
                "obv_change_20": -1.0,
                "ad_change_20": 2_000_000.0,
            },
            {
                "ticker": "FALLAD",
                "price": 110.0,
                "ma20": 100.0,
                "rsi14": 60.0,
                "obv_change_20": 5_000_000.0,
                "ad_change_20": -1.0,
            },
        ]

        result = filter_technical_candidates(
            technical_rows,
            min_rsi=50.0,
            require_above_ma20=True,
            require_rising_obv=True,
            require_rising_ad=True,
        )

        self.assertEqual(
            [candidate["ticker"] for candidate in result],
            ["PASS"],
        )

    def test_filters_candidates_by_price_and_liquidity(self) -> None:
        """Only stocks meeting every configured threshold remain."""
        market_rows = [
            {
                "ticker": "NVDA",
                "price": 180.0,
                "average_volume": 2_000_000,
            },
            {
                "ticker": "CHEAP",
                "price": 3.0,
                "average_volume": 5_000_000,
            },
            {
                "ticker": "THIN",
                "price": 50.0,
                "average_volume": 50_000,
            },
            {
                "ticker": "MISSING",
                "price": None,
                "average_volume": 1_000_000,
            },
        ]

        result = filter_market_candidates(
            market_rows,
            min_price=5.0,
            min_average_volume=500_000,
            min_average_dollar_volume=20_000_000,
        )

        self.assertEqual(
            result,
            [
                {
                    "ticker": "NVDA",
                    "price": 180.0,
                    "average_volume": 2_000_000,
                    "average_dollar_volume": 360_000_000.0,
                }
            ],
        )
    def test_collects_price_and_average_volume_rows(self) -> None:
        """Batch market data becomes rows used by the liquidity filter."""
        columns = pd.MultiIndex.from_tuples(
            [
                ("Close", "MSFT"),
                ("Close", "NVDA"),
                ("Volume", "MSFT"),
                ("Volume", "NVDA"),
            ]
        )
        history = pd.DataFrame(
            [
                [420.0, 180.0, 900_000, 1_800_000],
                [421.0, 182.0, 1_100_000, 2_200_000],
            ],
            columns=columns,
        )

        with patch(
            "modules.market_scanner.yf.download",
            return_value=history,
        ) as downloader:
            result = collect_market_rows(["NVDA", "MSFT"])

        self.assertEqual(
            result,
            [
                {
                    "ticker": "MSFT",
                    "price": 421.0,
                    "average_volume": 1_000_000,
                },
                {
                    "ticker": "NVDA",
                    "price": 182.0,
                    "average_volume": 2_000_000,
                },
            ],
        )
        downloader.assert_called_once()
    def test_splits_market_downloads_into_batches(self) -> None:
        """A large universe is downloaded in configured-size batches."""
        first_columns = pd.MultiIndex.from_tuples(
            [
                ("Close", "AAPL"),
                ("Close", "MSFT"),
                ("Volume", "AAPL"),
                ("Volume", "MSFT"),
            ]
        )
        first_history = pd.DataFrame(
            [[200.0, 420.0, 1_000_000, 900_000]],
            columns=first_columns,
        )
        second_history = pd.DataFrame(
            {
                "Close": [180.0],
                "Volume": [2_000_000],
            }
        )

        with patch(
            "modules.market_scanner.yf.download",
            side_effect=[first_history, second_history],
        ) as downloader:
            result = collect_market_rows(
                ["NVDA", "MSFT", "AAPL"],
                batch_size=2,
            )

        self.assertEqual(
            [row["ticker"] for row in result],
            ["AAPL", "MSFT", "NVDA"],
        )
        self.assertEqual(downloader.call_count, 2)
    def test_continues_after_one_market_batch_fails(self) -> None:
        """One provider batch failure does not stop later batches."""
        successful_history = pd.DataFrame(
            {
                "Close": [182.0],
                "Volume": [2_000_000],
            }
        )

        with patch(
            "modules.market_scanner.yf.download",
            side_effect=[
                RuntimeError("temporary provider failure"),
                successful_history,
            ],
        ) as downloader:
            result = collect_market_rows(
                ["AAPL", "NVDA"],
                batch_size=1,
            )

        self.assertEqual(
            result,
            [
                {
                    "ticker": "NVDA",
                    "price": 182.0,
                    "average_volume": 2_000_000,
                }
            ],
        )
        self.assertEqual(downloader.call_count, 2)
    def test_connects_liquidity_and_technical_scan_stages(self) -> None:
        """The combined scan runs liquidity collection before technical rules."""
        liquidity_candidates = [
            {
                "ticker": "NVDA",
                "price": 220.0,
                "average_volume": 1_000_000,
                "average_dollar_volume": 220_000_000.0,
            }
        ]
        technical_rows = [
            {
                "ticker": "NVDA",
                "price": 220.0,
                "ma20": 210.0,
                "rsi14": 60.0,
                "obv_change_20": 5_000_000.0,
                "ad_change_20": 2_000_000.0,
            }
        ]

        with (
            patch(
                "modules.market_scanner.scan_us_market",
                return_value=liquidity_candidates,
            ) as liquidity_scanner,
            patch(
                "modules.market_scanner.collect_technical_rows",
                return_value=technical_rows,
            ) as technical_collector,
            patch(
                "modules.market_scanner.filter_technical_candidates",
                return_value=technical_rows,
            ) as technical_filter,
        ):
            result = scan_us_market_technical_candidates(
                min_price=5.0,
                min_average_volume=500_000,
                min_average_dollar_volume=20_000_000,
                min_rsi=50.0,
                require_above_ma20=True,
                require_rising_obv=True,
                require_rising_ad=True,
                batch_size=50,
            )

        self.assertEqual(result, technical_rows)
        liquidity_scanner.assert_called_once_with(
            min_price=5.0,
            min_average_volume=500_000,
            min_average_dollar_volume=20_000_000,
            batch_size=50,
        )
        technical_collector.assert_called_once_with(
            liquidity_candidates,
            batch_size=50,
        )
        technical_filter.assert_called_once_with(
            technical_rows,
            min_rsi=50.0,
            require_above_ma20=True,
            require_rising_obv=True,
            require_rising_ad=True,
        )

    def test_scans_market_from_universe_to_candidates(self) -> None:
        """The full scan connects universe, market data, and filtering."""
        universe = ["AAPL", "NVDA"]
        market_rows = [
            {
                "ticker": "NVDA",
                "price": 182.0,
                "average_volume": 2_000_000,
            }
        ]
        candidates = [
            {
                "ticker": "NVDA",
                "price": 182.0,
                "average_volume": 2_000_000,
                "average_dollar_volume": 364_000_000.0,
            }
        ]

        with (
            patch(
                "modules.market_scanner.collect_us_market_universe",
                return_value=universe,
            ) as universe_collector,
            patch(
                "modules.market_scanner.collect_market_rows",
                return_value=market_rows,
            ) as market_collector,
            patch(
                "modules.market_scanner.filter_market_candidates",
                return_value=candidates,
            ) as candidate_filter,
        ):
            result = scan_us_market(
                min_price=5.0,
                min_average_volume=500_000,
                min_average_dollar_volume=20_000_000,
                batch_size=50,
            )

        self.assertEqual(result, candidates)
        universe_collector.assert_called_once_with()
        market_collector.assert_called_once_with(
            universe,
            batch_size=50,
        )
        candidate_filter.assert_called_once_with(
            market_rows,
            min_price=5.0,
            min_average_volume=500_000,
            min_average_dollar_volume=20_000_000,
        )

    def test_rejects_negative_scanner_thresholds(self) -> None:
        """Negative price or liquidity settings raise a clear error."""
        with self.assertRaisesRegex(
            ValueError,
            "scanner thresholds cannot be negative",
        ):
            filter_market_candidates(
                [],
                min_price=-1.0,
                min_average_volume=500_000,
                min_average_dollar_volume=20_000_000,
            )


if __name__ == "__main__":
    unittest.main()