"""Tests for stock market data validation and indicator calculations."""

import unittest
from datetime import datetime, timezone

import pandas as pd

from modules.market_data import (
    build_market_metadata,
    calculate_indicators,
    normalize_ticker,
)


class MarketDataTests(unittest.TestCase):
    """Verify the core market-data functions without using the internet."""

    def test_normalize_ticker_uppercases_input(self) -> None:
        """Lowercase tickers are cleaned and converted to uppercase."""
        self.assertEqual(normalize_ticker(" nvda "), "NVDA")

    def test_normalize_ticker_rejects_invalid_input(self) -> None:
        """Empty or unsafe ticker values raise ValueError."""
        with self.assertRaises(ValueError):
            normalize_ticker("")

        with self.assertRaises(ValueError):
            normalize_ticker("../NVDA")

    def test_calculate_indicators_adds_expected_columns(self) -> None:
        """Moving averages, OBV, A/D, and RSI14 are calculated from OHLCV data."""
        data = pd.DataFrame(
            {
        "High": [value + 2 for value in range(1, 61)],
        "Low": [value - 1 for value in range(1, 61)],
        "Close": list(range(1, 61)),
        "Volume": [100] * 60,
            }
        )

        result = calculate_indicators(data)

        self.assertIn("MA20", result.columns)
        self.assertIn("MA60", result.columns)
        self.assertIn("MA150", result.columns)
        self.assertIn("MA200", result.columns)
        self.assertIn("VOLUME20", result.columns)
        self.assertIn("OBV", result.columns)
        self.assertIn("AD", result.columns)
        self.assertAlmostEqual(result["AD"].iloc[-1], -2000.0)
        self.assertIn("RSI14", result.columns)
        self.assertAlmostEqual(result["MA20"].iloc[-1], 50.5)
        self.assertAlmostEqual(result["MA60"].iloc[-1], 30.5)
        self.assertEqual(result["OBV"].iloc[-1], 5900)
        self.assertAlmostEqual(result["RSI14"].iloc[-1], 100.0)

    def test_build_market_metadata_reports_source_time_and_status(self) -> None:
        """Report metadata identifies source, collection time, and data status."""
        data = pd.DataFrame(
            {"Close": [100.0]},
            index=pd.to_datetime(["2026-07-20"]),
        )
        collected_at = datetime(2026, 7, 21, 12, 30, tzinfo=timezone.utc)

        metadata = build_market_metadata(data, collected_at=collected_at)

        self.assertEqual(metadata["source"], "Yahoo Finance via yfinance")
        self.assertEqual(metadata["collected_at_utc"], "2026-07-21 12:30:00 UTC")
        self.assertEqual(metadata["market_date"], "2026-07-20")
        self.assertEqual(
            metadata["market_status"],
            "Latest completed/available daily session",
        )
if __name__ == "__main__":
    unittest.main()