"""Test persistent watchlist management without changing real user data."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import watchlist


class WatchlistTests(unittest.TestCase):
    """Verify ticker validation, storage, addition, and removal."""

    def setUp(self):
        """Create a separate temporary watchlist before each test."""
        self.temp_directory = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_directory.name) / "watchlist.json"

        self.path_patch = patch.object(
            watchlist,
            "WATCHLIST_PATH",
            self.test_path,
        )
        self.path_patch.start()

    def tearDown(self):
        """Restore the real path and delete temporary test data."""
        self.path_patch.stop()
        self.temp_directory.cleanup()

    def test_normalize_ticker(self):
        """Ticker input is trimmed and converted to uppercase."""
        self.assertEqual(watchlist.normalize_ticker(" nvda "), "NVDA")
        self.assertEqual(watchlist.normalize_ticker("brk.b"), "BRK.B")

    def test_normalize_ticker_rejects_invalid_value(self):
        """Empty or unsafe ticker input is rejected."""
        with self.assertRaises(ValueError):
            watchlist.normalize_ticker("")

        with self.assertRaises(ValueError):
            watchlist.normalize_ticker("NVDA/TEST")

    def test_load_watchlist_returns_empty_list_when_missing(self):
        """A new user starts with an empty watchlist."""
        self.assertEqual(watchlist.load_watchlist(), [])

    def test_save_and_load_watchlist(self):
        """Saved tickers are normalized, deduplicated, and sorted."""
        watchlist.save_watchlist(["msft", "NVDA", "msft"])

        self.assertEqual(
            watchlist.load_watchlist(),
            ["MSFT", "NVDA"],
        )

    def test_add_to_watchlist_prevents_duplicates(self):
        """Adding the same ticker twice does not create duplicates."""
        self.assertEqual(
            watchlist.add_to_watchlist("nvda"),
            ("NVDA", True),
        )
        self.assertEqual(
            watchlist.add_to_watchlist("NVDA"),
            ("NVDA", False),
        )
        self.assertEqual(watchlist.load_watchlist(), ["NVDA"])

    def test_remove_from_watchlist(self):
        """A saved ticker can be removed."""
        watchlist.save_watchlist(["NVDA", "MSFT"])

        self.assertEqual(
            watchlist.remove_from_watchlist("nvda"),
            ("NVDA", True),
        )
        self.assertEqual(watchlist.load_watchlist(), ["MSFT"])

    def test_remove_missing_ticker_is_safe(self):
        """Removing an unregistered ticker returns False."""
        self.assertEqual(
            watchlist.remove_from_watchlist("NOW"),
            ("NOW", False),
        )

    def test_load_watchlist_rejects_invalid_json(self):
        """A damaged JSON file produces a clear error."""
        self.test_path.write_text("{broken", encoding="utf-8")

        with self.assertRaises(ValueError):
            watchlist.load_watchlist()

    def test_load_watchlist_ignores_damaged_entries(self):
        """Valid tickers remain usable when individual entries are damaged."""
        self.test_path.write_text(
            json.dumps(["NVDA", "", 123, "MSFT", "BAD/TICKER"]),
            encoding="utf-8",
        )

        self.assertEqual(
            watchlist.load_watchlist(),
            ["MSFT", "NVDA"],
        )


if __name__ == "__main__":
    unittest.main()