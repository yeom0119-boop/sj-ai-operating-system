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

    def test_print_menu_shows_v1_5_options(self) -> None:
        """The menu displays the required v1.5 labels."""
        buffer = io.StringIO()

        with patch("sys.stdout", buffer):
            main.print_menu()

        output = buffer.getvalue()
        self.assertIn("SJ AI Operating System v1.5", output)
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
        self.assertIn("15. Exit", output)

    def test_main_rejects_invalid_choice(self) -> None:
        """Invalid menu input prints an error and keeps running until Exit."""
        inputs = iter(["16", "15"])
        buffer = io.StringIO()

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch("sys.stdout", buffer):
                main.main()

        output = buffer.getvalue()
        self.assertIn("Error: please enter a number from 1 to 15.", output)
        self.assertIn("Goodbye.", output)

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
        inputs = iter(["14", "15"])

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch(
                "main.handle_generate_watchlist_reports"
            ) as batch_handler:
                with patch("sys.stdout", io.StringIO()):
                    main.main()

        batch_handler.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
