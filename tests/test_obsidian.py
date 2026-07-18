"""
SJ AI Operating System
tests/test_obsidian.py

Unit tests for vault operations in modules/obsidian.py.

Role:
- Verify daily and stock note creation behavior
- Verify stock note read/list helpers
- Verify vault search and recent-note listing
- Run against a temporary vault so real user notes are never modified
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from modules import obsidian


class ObsidianModuleTests(unittest.TestCase):
    """Tests for Obsidian vault helper functions."""

    def setUp(self) -> None:
        """Create an isolated temporary vault for each test."""

        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self.temp_dir.name) / "vault"
        self.vault_root.mkdir()
        self.patchers = [
            patch.object(obsidian, "get_vault_root", return_value=self.vault_root),
        ]

        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        """Stop patches and remove the temporary vault."""

        for patcher in reversed(self.patchers):
            patcher.stop()

        self.temp_dir.cleanup()

    def test_sanitize_stock_name_uppercases_and_strips_invalid_chars(self) -> None:
        """Tickers are uppercased and unsafe filename characters are removed."""

        self.assertEqual(obsidian.sanitize_stock_name("nvda"), "NVDA")
        self.assertEqual(obsidian.sanitize_stock_name(" aa:pl/tr "), "AAPLTR")

    def test_sanitize_stock_name_rejects_empty_input(self) -> None:
        """Empty or invalid tickers raise ValueError."""

        with self.assertRaises(ValueError):
            obsidian.sanitize_stock_name("   ")

    def test_create_daily_note_creates_expected_file(self) -> None:
        """Daily notes use YYYY-MM-DD.md inside vault/Daily/."""

        target_date = date(2026, 7, 18)
        file_path, action = obsidian.create_daily_note(note_date=target_date)

        self.assertEqual(action, "create")
        self.assertEqual(file_path.name, "2026-07-18.md")
        self.assertTrue(file_path.parent.name == "Daily")
        self.assertTrue(file_path.exists())

        content = file_path.read_text(encoding="utf-8")
        self.assertIn("Daily Note — 2026-07-18", content)

    def test_create_daily_note_does_not_overwrite_existing(self) -> None:
        """Existing daily notes are left unchanged."""

        target_date = date(2026, 7, 18)
        daily_folder = self.vault_root / "Daily"
        daily_folder.mkdir(parents=True)
        existing_path = daily_folder / "2026-07-18.md"
        existing_path.write_text("# Existing daily note\n", encoding="utf-8")

        file_path, action = obsidian.create_daily_note(note_date=target_date)

        self.assertEqual(action, "exists")
        self.assertEqual(existing_path.read_text(encoding="utf-8"), "# Existing daily note\n")

    def test_create_stock_note_uppercases_ticker(self) -> None:
        """Stock notes are stored as uppercase .md files in vault/Stocks/."""

        file_path, action = obsidian.create_stock_note("tsla")

        self.assertEqual(action, "create")
        self.assertEqual(file_path.name, "TSLA.md")
        self.assertTrue(file_path.parent.name == "Stocks")
        self.assertIn("# TSLA", file_path.read_text(encoding="utf-8"))

    def test_create_stock_note_does_not_overwrite_existing(self) -> None:
        """Existing stock notes are preserved."""

        stocks_folder = self.vault_root / "Stocks"
        stocks_folder.mkdir(parents=True)
        existing_path = stocks_folder / "NVDA.md"
        existing_path.write_text("# Existing NVDA note\n", encoding="utf-8")

        file_path, action = obsidian.create_stock_note("nvda")

        self.assertEqual(action, "exists")
        self.assertEqual(existing_path.read_text(encoding="utf-8"), "# Existing NVDA note\n")

    def test_read_stock_note_uppercases_symbol(self) -> None:
        """read_stock_note resolves lowercase input to uppercase files."""

        stocks_folder = self.vault_root / "Stocks"
        stocks_folder.mkdir(parents=True)
        note_path = stocks_folder / "NVDA.md"
        note_path.write_text("# NVDA\nGPU analysis\n", encoding="utf-8")

        content = obsidian.read_stock_note("nvda")

        self.assertIn("GPU analysis", content)

    def test_read_stock_note_returns_empty_when_missing(self) -> None:
        """Missing stock notes return an empty string."""

        self.assertEqual(obsidian.read_stock_note("MSFT"), "")

    def test_read_stock_note_rejects_empty_symbol(self) -> None:
        """Empty symbols raise ValueError."""

        with self.assertRaises(ValueError):
            obsidian.read_stock_note("   ")

    def test_list_stock_notes_returns_sorted_tickers(self) -> None:
        """list_stock_notes returns alphabetically sorted uppercase tickers."""

        stocks_folder = self.vault_root / "Stocks"
        stocks_folder.mkdir(parents=True)
        (stocks_folder / "NVDA.md").write_text("# NVDA\n", encoding="utf-8")
        (stocks_folder / "AAPL.md").write_text("# AAPL\n", encoding="utf-8")

        self.assertEqual(obsidian.list_stock_notes(), ["AAPL", "NVDA"])

    def test_list_stock_notes_returns_empty_when_folder_missing(self) -> None:
        """list_stock_notes returns an empty list when Stocks/ does not exist."""

        self.assertEqual(obsidian.list_stock_notes(), [])

    def test_search_vault_matches_filename_and_content(self) -> None:
        """Search scans the vault recursively for filename and content matches."""

        daily_folder = self.vault_root / "Daily"
        stocks_folder = self.vault_root / "Stocks"
        daily_folder.mkdir(parents=True)
        stocks_folder.mkdir(parents=True)

        (daily_folder / "2026-07-18.md").write_text("# Daily\n", encoding="utf-8")
        (stocks_folder / "NVDA.md").write_text("GPU demand remains strong\n", encoding="utf-8")
        (stocks_folder / "AAPL.md").write_text("Services revenue growth\n", encoding="utf-8")

        results = obsidian.search_vault("nvda")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["relative_path"], Path("Stocks") / "NVDA.md")
        self.assertTrue(results[0]["filename_match"])
        self.assertFalse(results[0]["content_match"])

        content_results = obsidian.search_vault("services")
        self.assertEqual(len(content_results), 1)
        self.assertTrue(content_results[0]["content_match"])

    def test_search_vault_returns_empty_for_blank_query(self) -> None:
        """Blank search terms return no results."""

        self.assertEqual(obsidian.search_vault(""), [])
        self.assertEqual(obsidian.search_vault("   "), [])

    def test_list_recent_notes_returns_newest_first(self) -> None:
        """Recent notes are sorted by modification time descending."""

        daily_folder = self.vault_root / "Daily"
        stocks_folder = self.vault_root / "Stocks"
        daily_folder.mkdir(parents=True)
        stocks_folder.mkdir(parents=True)

        older_path = daily_folder / "older.md"
        newer_path = stocks_folder / "newer.md"
        older_path.write_text("older\n", encoding="utf-8")
        newer_path.write_text("newer\n", encoding="utf-8")

        older_time = datetime.now() - timedelta(days=1)
        newer_time = datetime.now()

        import os

        os.utime(older_path, (older_time.timestamp(), older_time.timestamp()))
        os.utime(newer_path, (newer_time.timestamp(), newer_time.timestamp()))

        recent = obsidian.list_recent_notes(limit=10)

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0][0], newer_path)
        self.assertEqual(recent[1][0], older_path)

    def test_legacy_save_stock_note_appends_without_deleting(self) -> None:
        """Legacy save helper still appends analysis to existing notes."""

        file_path, action = obsidian.save_stock_note("msft", "First entry")
        self.assertEqual(action, "create")

        append_path, append_action = obsidian.save_stock_note("msft", "Second entry")
        self.assertEqual(append_action, "append")
        self.assertEqual(append_path, file_path)

        content = file_path.read_text(encoding="utf-8")
        self.assertIn("First entry", content)
        self.assertIn("Second entry", content)


if __name__ == "__main__":
    unittest.main()
