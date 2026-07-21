"""Tests for the institutional-footprint scoring module."""

import unittest
from unittest.mock import patch
import pandas as pd

from modules.institutional_footprint import (
    build_footprint_report,
    calculate_footprint_scores,
)


def build_indicator_data(
    close: float,
    ma20: float,
    ma60: float,
    volume: float,
    volume20: float,
    obv_values: list[float],
    rsi14: float,
) -> pd.DataFrame:
    """Build controlled indicator rows for score tests.

    Input: indicator values used by the scoring rules.
    Output: DataFrame matching calculate_indicators() output.
    Role: test scoring without downloading live market data.
    """
    return pd.DataFrame(
        {
            "Close": [close] * len(obv_values),
            "Volume": [volume] * len(obv_values),
            "MA20": [ma20] * len(obv_values),
            "MA60": [ma60] * len(obv_values),
            "VOLUME20": [volume20] * len(obv_values),
            "OBV": obv_values,
            "RSI14": [rsi14] * len(obv_values),
        }
    )


def build_options_snapshot(
    put_call_oi_ratio: float,
    put_call_volume_ratio: float,
) -> dict:
    """Build a controlled options snapshot.

    Input: Put/Call OI and volume ratios.
    Output: options snapshot dictionary.
    Role: isolate option-ratio effects in scoring tests.
    """
    return {
        "ticker": "TEST",
        "expirations": [
            {
                "put_call_oi_ratio": put_call_oi_ratio,
                "put_call_volume_ratio": put_call_volume_ratio,
            }
        ],
    }


class FootprintScoreTests(unittest.TestCase):
    """Verify bullish, bearish, and missing-data behavior."""

    def test_strong_money_in_signals_score_100(self) -> None:
        """Aligned bullish evidence produces the maximum Money In score."""
        indicators = build_indicator_data(
            close=110,
            ma20=105,
            ma60=100,
            volume=150,
            volume20=100,
            obv_values=[100, 110, 120, 130, 140, 160],
            rsi14=60,
        )
        options = build_options_snapshot(0.5, 0.6)

        result = calculate_footprint_scores(indicators, options)

        self.assertEqual(result["money_in_score"], 100)
        self.assertEqual(result["money_out_score"], 0)
        self.assertEqual(result["data_coverage"], 100)

    def test_strong_money_out_signals_score_100(self) -> None:
        """Aligned bearish evidence produces the maximum Money Out score."""
        indicators = build_indicator_data(
            close=90,
            ma20=95,
            ma60=100,
            volume=150,
            volume20=100,
            obv_values=[160, 150, 140, 130, 120, 100],
            rsi14=40,
        )
        options = build_options_snapshot(1.2, 1.3)

        result = calculate_footprint_scores(indicators, options)

        self.assertEqual(result["money_in_score"], 0)
        self.assertEqual(result["money_out_score"], 100)
        self.assertEqual(result["data_coverage"], 100)

    def test_missing_options_reduces_data_coverage(self) -> None:
        """Missing option ratios do not crash technical scoring."""
        indicators = build_indicator_data(
            close=110,
            ma20=105,
            ma60=100,
            volume=100,
            volume20=100,
            obv_values=[100, 110, 120, 130, 140, 150],
            rsi14=50,
        )
        options = {"ticker": "TEST", "expirations": []}

        result = calculate_footprint_scores(indicators, options)

        self.assertEqual(result["data_coverage"], 80)
        self.assertGreater(result["money_in_score"], result["money_out_score"])

    def test_empty_indicator_data_raises_error(self) -> None:
        """The scorer rejects input without usable indicator rows."""
        indicators = pd.DataFrame(
            columns=[
                "Close",
                "Volume",
                "MA20",
                "MA60",
                "VOLUME20",
                "OBV",
                "RSI14",
            ]
        )

        with self.assertRaises(ValueError):
            calculate_footprint_scores(
                indicators,
                {"ticker": "TEST", "expirations": []},
            )

class FootprintReportTests(unittest.TestCase):
    """Verify the Markdown footprint report output."""

    @patch("modules.institutional_footprint.calculate_footprint_scores")
    @patch("modules.institutional_footprint.collect_options_snapshot")
    @patch("modules.institutional_footprint.calculate_indicators")
    @patch("modules.institutional_footprint.fetch_stock_history")
    def test_report_shows_option_expiration_scope(
        self,
        mock_fetch_history,
        mock_calculate_indicators,
        mock_collect_options,
        mock_calculate_scores,
    ) -> None:
        """Report shows analyzed expirations and the ratio method."""
        mock_fetch_history.return_value = object()
        mock_calculate_indicators.return_value = object()
        mock_collect_options.return_value = {
            "analyzed_expirations": 3,
            "expiration_count": 23,
        }
        mock_calculate_scores.return_value = {
            "ticker": "NVDA",
            "money_in_score": 60,
            "money_out_score": 15,
            "data_coverage": 100,
            "market_inputs": {
                "close": 203.28,
                "ma20": 201.87,
                "ma60": 208.90,
                "volume_ratio": 1.10,
                "obv_change": 1000,
                "rsi14": 59.10,
                "put_call_oi_ratio": 0.70,
                "put_call_volume_ratio": 0.58,
            },
            "signals": [],
            "warning": "Research signal only.",
        }

        report = build_footprint_report("NVDA", expiration_limit=3)

        self.assertIn(
            "**Analyzed option expirations**: 3 of 23",
            report,
        )
        self.assertIn(
            "**Option ratio method**: Simple average of per-expiration ratios",
            report,
        )
        mock_collect_options.assert_called_once_with(
            "NVDA",
            expiration_limit=3,
        )
if __name__ == "__main__":
    unittest.main()