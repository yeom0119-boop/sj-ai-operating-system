"""
SJ AI Operating System
tests/test_main.py

Smoke tests for the interactive CLI entry point in main.py.

Role:
- Verify the v0.3 menu text
- Verify invalid menu input is handled without exiting
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import main


class MainMenuTests(unittest.TestCase):
    """Tests for main.py menu behavior."""

    def test_print_menu_shows_v0_3_options(self) -> None:
        """The menu displays the required v0.3 labels."""

        buffer = io.StringIO()

        with patch("sys.stdout", buffer):
            main.print_menu()

        output = buffer.getvalue()

        self.assertIn("SJ AI Operating System v0.3", output)
        self.assertIn("1. Create daily note", output)
        self.assertIn("2. Create stock note", output)
        self.assertIn("3. Read stock note", output)
        self.assertIn("4. List stock notes", output)
        self.assertIn("5. Exit", output)

    def test_main_rejects_invalid_choice(self) -> None:
        """Invalid menu input prints an error and keeps running until Exit."""

        inputs = iter(["9", "5"])
        buffer = io.StringIO()

        with patch("builtins.input", lambda _prompt="": next(inputs)):
            with patch("sys.stdout", buffer):
                main.main()

        output = buffer.getvalue()
        self.assertIn("Error: please enter a number from 1 to 5.", output)
        self.assertIn("Goodbye.", output)


if __name__ == "__main__":
    unittest.main()
