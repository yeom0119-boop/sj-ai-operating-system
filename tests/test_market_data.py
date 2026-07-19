"""Tests for stock market data validation and indicator calculations."""

import unittest

import pandas as pd

from modules.market_data import calculate_indicators, normalize_ticker


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
        """MA20, MA60, OBV, and RSI14 are calculated from OHLCV data."""
        data = pd.DataFrame(
            {
                "Close": list(range(1, 61)),
                "Volume": [100] * 60,
            }
        )

        result = calculate_indicators(data)

        self.assertIn("MA20", result.columns)
        self.assertIn("MA60", result.columns)
        self.assertIn("OBV", result.columns)
        self.assertIn("RSI14", result.columns)
        self.assertAlmostEqual(result["MA20"].iloc[-1], 50.5)
        self.assertAlmostEqual(result["MA60"].iloc[-1], 30.5)
        self.assertEqual(result["OBV"].iloc[-1], 5900)
        self.assertAlmostEqual(result["RSI14"].iloc[-1], 100.0)


if __name__ == "__main__":
    unittest.main()