"""Test options-footprint collection without live provider requests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from modules.options_data import (
    build_options_report,
    collect_options_snapshot,
)


class OptionsDataTests(unittest.TestCase):
    """Verify option-chain calculations and Markdown formatting."""

    def test_collect_options_snapshot_calculates_ratios(self) -> None:
        """Call/put totals and maximum-OI contracts are calculated."""
        calls = pd.DataFrame(
            [
                {
                    "contractSymbol": "NVDA_CALL_200",
                    "strike": 200.0,
                    "openInterest": 100,
                    "volume": 50,
                    "impliedVolatility": 0.40,
                },
                {
                    "contractSymbol": "NVDA_CALL_210",
                    "strike": 210.0,
                    "openInterest": 300,
                    "volume": 150,
                    "impliedVolatility": 0.50,
                },
            ]
        )
        puts = pd.DataFrame(
            [
                {
                    "contractSymbol": "NVDA_PUT_190",
                    "strike": 190.0,
                    "openInterest": 200,
                    "volume": 100,
                    "impliedVolatility": 0.60,
                }
            ]
        )

        fake_stock = MagicMock()
        fake_stock.options = ("2026-07-20",)
        fake_stock.history.return_value = pd.DataFrame(
            {"Close": [202.81]}
        )
        fake_stock.option_chain.return_value = SimpleNamespace(
            calls=calls,
            puts=puts,
        )

        with patch(
            "modules.options_data.yf.Ticker",
            return_value=fake_stock,
        ):
            snapshot = collect_options_snapshot("nvda", 1)

        expiration = snapshot["expirations"][0]
        self.assertEqual(snapshot["ticker"], "NVDA")
        self.assertEqual(snapshot["current_price"], 202.81)
        self.assertEqual(expiration["call_open_interest"], 400.0)
        self.assertEqual(expiration["put_open_interest"], 200.0)
        self.assertEqual(expiration["put_call_oi_ratio"], 0.5)
        self.assertEqual(
            expiration["largest_call_oi"]["strike"],
            210.0,
        )

    def test_collect_options_snapshot_rejects_zero_limit(self) -> None:
        """At least one expiration must be requested."""
        with self.assertRaises(ValueError):
            collect_options_snapshot("NVDA", 0)

    def test_collect_options_snapshot_handles_missing_options(self) -> None:
        """A ticker without listed options produces a clear error."""
        fake_stock = MagicMock()
        fake_stock.options = ()

        with patch(
            "modules.options_data.yf.Ticker",
            return_value=fake_stock,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "no listed options",
            ):
                collect_options_snapshot("NVDA", 1)

    def test_build_options_report_formats_snapshot(self) -> None:
        """A collected snapshot becomes a readable Markdown report."""
        snapshot = {
            "ticker": "NVDA",
            "current_price": 202.81,
            "expiration_count": 1,
            "analyzed_expirations": 1,
            "source": "Test provider",
            "expirations": [
                {
                    "expiration": "2026-07-20",
                    "call_open_interest": 400.0,
                    "put_open_interest": 200.0,
                    "put_call_oi_ratio": 0.5,
                    "call_volume": 200.0,
                    "put_volume": 100.0,
                    "put_call_volume_ratio": 0.5,
                    "largest_call_oi": {
                        "contract": "NVDA_CALL_210",
                        "strike": 210.0,
                        "open_interest": 300.0,
                        "volume": 150.0,
                        "implied_volatility": 0.50,
                    },
                    "largest_put_oi": {
                        "contract": "NVDA_PUT_190",
                        "strike": 190.0,
                        "open_interest": 200.0,
                        "volume": 100.0,
                        "implied_volatility": 0.60,
                    },
                    "unusual_candidates": [
                        {
                            "type": "Call",
                            "contract": "NVDA_CALL_210",
                            "strike": 210.0,
                            "open_interest": 300.0,
                            "volume": 150.0,
                            "volume_oi_ratio": 0.5,
                            "implied_volatility": 0.50,
                        }
                    ],
                }
            ],
        }

        with patch(
            "modules.options_data.collect_options_snapshot",
            return_value=snapshot,
        ):
            report = build_options_report("NVDA", 1)

        self.assertIn("# Options Footprint Report", report)
        self.assertIn("Put/Call OI ratio**: 0.50", report)
        self.assertIn("$210.00", report)
        self.assertIn("Test provider", report)
        self.assertIn("not proof of institutional", report)


if __name__ == "__main__":
    unittest.main()