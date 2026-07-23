"""
SJ AI Operating System
tests/test_main.py

Smoke tests for the interactive CLI entry point in main.py.

Role:
- Verify the v1.1 menu text
- Verify invalid menu input is handled without exiting
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import main


class MainMenuTests(unittest.TestCase):
    """Tests for main.py menu behavior."""

    def test_print_menu_shows_v2_0_options(self) -> None:
        """The menu displays the required v2.0 labels."""
        buffer = io.StringIO()

        with patch("sys.stdout", buffer):
            main.print_menu()

        output = buffer.getvalue()
        self.assertIn("SJ AI Operating System v2.0", output)
        self.assertIn("1. Create daily note", output)
        self.assertIn("2. Create stock note", output)
        self.assertIn("3. Read stock note", output)
        self.assertIn("4. List stock notes", output)
        self.assertIn("5. Add stock analysis", output)
        self.assertIn("6. Search all notes", output)
        self.assertIn("7. List recent notes", output)
        self.assertIn("8. Generate automated stock report", output)
        self.assertIn("9. Generate official SEC filings report", output)
        self.assertIn("10. Generate Gemini SEC guidance analysis", output)
        self.assertIn("11. List watchlist", output)
        self.assertIn("12. Add stock to watchlist", output)
        self.assertIn("13. Remove stock from watchlist", output)
        self.assertIn(
            "15. Generate integrated analysis for all watchlist stocks",
            output,
        )
        self.assertIn(
            "16. Generate options reports for all watchlist stocks",
            output,
        )
        self.assertIn("17. Generate footprint radar for all watchlist stocks", output)
        self.assertIn("18. Run full U.S. Market Scanner", output)
        self.assertIn("19. Exit", output)

    def test_main_rejects_invalid_choice(self) -> None:
        """Invalid menu input prints an error and keeps running until Exit."""
        inputs = iter(["20", "19"])
        buffer = io.StringIO()

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch("sys.stdout", buffer):
                main.main()

        output = buffer.getvalue()
        self.assertIn("Error: please enter a number from 1 to 19.", output)
        self.assertIn("Goodbye.", output)
    def test_menu_option_18_runs_market_scanner(self) -> None:
        """Menu option 18 starts the Market Scanner and option 19 exits."""
        inputs = iter(["18", "19"])

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch("main.handle_scan_us_market") as scanner_handler:
                with patch("sys.stdout", io.StringIO()):
                    main.main()

        scanner_handler.assert_called_once_with()


class MarketScannerHandlerTests(unittest.TestCase):
    """Tests for the configured full-market scan handler."""

    def test_scanner_uses_config_and_prints_candidates(self) -> None:
        """Configured thresholds reach the scanner and results are shown."""
        config = {
            "min_price": 5.0,
            "min_average_volume": 500000,
            "min_average_dollar_volume": 20000000,
            "min_rsi": 50.0,
            "require_above_ma20": True,
            "require_rising_obv": True,
            "require_rising_ad": True,
            "batch_size": 100,
            "max_candidates": 10,
        }
        candidates = [
            {
            "ticker": "NVDA",
            "price": 202.81,
            "rsi14": 61.25,
            "price_vs_ma20_pct": 3.5,
            "obv_change_ratio_20": 0.4,
            "ad_change_ratio_20": 0.3,
            }
        ]
        buffer = io.StringIO()

        with patch(
            "main.load_market_scanner_config",
            return_value=config,
        ):
            with patch(
                "main.scan_us_market_technical_candidates",
                return_value=candidates,
            ) as scanner:
                with patch("sys.stdout", buffer):
                    main.handle_scan_us_market()

        scanner.assert_called_once_with(
            min_price=5.0,
            min_average_volume=500000,
            min_average_dollar_volume=20000000.0,
            min_rsi=50.0,
            require_above_ma20=True,
            require_rising_obv=True,
            require_rising_ad=True,
            batch_size=100,
        )
        output = buffer.getvalue()
        self.assertIn("Candidates: 1", output)
        self.assertIn("NVDA", output)
        self.assertIn("RSI14: 61.25", output)


class WatchlistReportTests(unittest.TestCase):
    """Tests for automated reports generated from the watchlist."""

    def test_empty_watchlist_stops_without_downloading(self) -> None:
        """No market request is made when the watchlist is empty."""
        buffer = io.StringIO()

        with patch("main.load_watchlist", return_value=[]):
            with patch("main.build_stock_report") as build_report:
                with patch("sys.stdout", buffer):
                    main.handle_generate_watchlist_reports()

        build_report.assert_not_called()
        self.assertIn("Watchlist is empty.", buffer.getvalue())

    def test_reports_continue_after_one_ticker_fails(self) -> None:
        """One provider failure does not stop the remaining batch."""
        buffer = io.StringIO()

        with patch(
            "main.load_watchlist",
            return_value=["MSFT", "NVDA"],
        ):
            with patch(
                "main.build_stock_report",
                side_effect=["MSFT report", RuntimeError("provider unavailable")],
            ) as build_report:
                with patch(
                    "main.save_stock_note",
                    return_value=("unused-path", "append"),
                ) as save_note:
                    with patch(
                        "main._relative_vault_path",
                        return_value="Stocks/MSFT.md",
                    ):
                        with patch("sys.stdout", buffer):
                            main.handle_generate_watchlist_reports()

        output = buffer.getvalue()
        self.assertEqual(build_report.call_count, 2)
        save_note.assert_called_once_with("MSFT", "MSFT report")
        self.assertIn("Successful: 1", output)
        self.assertIn("Failed: 1", output)
        self.assertIn("NVDA: provider unavailable", output)

    def test_menu_option_14_runs_watchlist_reports(self) -> None:
        """Menu option 14 starts batch generation and option 15 exits."""
        inputs = iter(["14", "19"])

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch(
                "main.handle_generate_watchlist_reports"
            ) as batch_handler:
                with patch("sys.stdout", io.StringIO()):
                    main.main()

        batch_handler.assert_called_once_with()

class IntegratedWatchlistAnalysisTests(unittest.TestCase):
    """Tests for the full watchlist research pipeline."""

    def test_empty_watchlist_stops_integrated_analysis(self) -> None:
        """No provider is called when the watchlist is empty."""
        buffer = io.StringIO()

        with patch("main.load_watchlist", return_value=[]):
            with patch("main.build_stock_report") as market_builder:
                with patch("main.analyze_sec_guidance") as analyzer:
                    with patch("sys.stdout", buffer):
                        main.handle_generate_watchlist_integrated_analysis()

        market_builder.assert_not_called()
        analyzer.assert_not_called()
        self.assertIn("Watchlist is empty.", buffer.getvalue())

    def test_integrated_analysis_continues_after_failure(self) -> None:
        """A failed ticker does not stop the remaining batch workflow."""
        buffer = io.StringIO()

        with (
            patch(
                "main.load_watchlist",
                return_value=["MSFT", "NVDA"],
            ),
            patch(
                "main.build_stock_report",
                side_effect=[
                    "MSFT market report",
                    RuntimeError("market unavailable"),
                ],
            ) as market_builder,
            patch(
                "main.build_options_report",
                return_value="MSFT options report",
            ) as options_builder,
            patch(
                "main.build_earnings_guidance_report",
                side_effect=["current guidance", "previous guidance"],
            ) as guidance_builder,
            patch(
                "main.analyze_sec_guidance",
                return_value="Gemini comparison",
            ) as analyzer,
            patch(
                "main.save_stock_note",
                return_value=("unused-path", "append"),
            ) as save_note,
            patch(
                "main._relative_vault_path",
                return_value="Stocks/MSFT.md",
            ),
            patch("sys.stdout", buffer),
        ):
            main.handle_generate_watchlist_integrated_analysis()

        output = buffer.getvalue()
        self.assertEqual(market_builder.call_count, 2)
        options_builder.assert_called_once_with("MSFT")
        self.assertEqual(guidance_builder.call_count, 2)
        guidance_builder.assert_any_call("MSFT", release_index=0)
        guidance_builder.assert_any_call("MSFT", release_index=1)
        analyzer.assert_called_once_with(
            "MSFT",
            (
                "# CURRENT EARNINGS GUIDANCE\n\ncurrent guidance"
                "\n\n# PREVIOUS EARNINGS GUIDANCE\n\nprevious guidance"
            ),
        )
        self.assertEqual(save_note.call_count, 1)
        saved_report = save_note.call_args.args[1]
        self.assertIn("MSFT market report", saved_report)
        self.assertIn("MSFT options report", saved_report)
        self.assertIn("Gemini comparison", saved_report)
        self.assertIn("Successful: 1", output)
        self.assertIn("Failed: 1", output)
        self.assertIn("NVDA: market unavailable", output)

    def test_menu_option_15_runs_integrated_analysis(self) -> None:
        """Menu option 15 starts integration and option 18 exits."""
        inputs = iter(["15", "19"])

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch(
                "main.handle_generate_watchlist_integrated_analysis"
            ) as integrated_handler:
                with patch("sys.stdout", io.StringIO()):
                    main.main()

        integrated_handler.assert_called_once_with()

class WatchlistFootprintReportTests(unittest.TestCase):
    """Verify watchlist footprint report generation."""

    def test_empty_watchlist_skips_footprint_generation(self) -> None:
        """An empty watchlist does not request market or options data."""
        buffer = io.StringIO()

        with patch("main.load_watchlist", return_value=[]):
            with patch("main.build_footprint_report") as report_builder:
                with patch("sys.stdout", buffer):
                    main.handle_generate_watchlist_footprint_reports()

        report_builder.assert_not_called()
        self.assertIn("Watchlist is empty.", buffer.getvalue())

    def test_footprint_generation_continues_after_failure(self) -> None:
        """One failed ticker does not stop the remaining watchlist."""
        buffer = io.StringIO()

        with (
            patch(
                "main.load_watchlist",
                return_value=["MSFT", "NVDA"],
            ),
            patch(
                "main.build_footprint_report",
                side_effect=[
                    "MSFT footprint report",
                    RuntimeError("options unavailable"),
                ],
            ) as report_builder,
            patch(
                "main.save_stock_note",
                return_value=("unused-path", "append"),
            ) as save_note,
            patch(
                "main._relative_vault_path",
                return_value="Stocks/MSFT.md",
            ),
            patch("sys.stdout", buffer),
        ):
            main.handle_generate_watchlist_footprint_reports()

        output = buffer.getvalue()
        self.assertEqual(report_builder.call_count, 2)
        save_note.assert_called_once_with(
            "MSFT",
            "MSFT footprint report",
        )
        self.assertIn("Successful: 1", output)
        self.assertIn("Failed: 1", output)
        self.assertIn("NVDA: options unavailable", output)

    def test_menu_option_17_runs_footprint_reports(self) -> None:
        """Menu option 17 starts footprint generation and option 18 exits."""
        inputs = iter(["17", "19"])

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch(
                "main.handle_generate_watchlist_footprint_reports"
            ) as footprint_handler:
                with patch("sys.stdout", io.StringIO()):
                    main.main()

        footprint_handler.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
