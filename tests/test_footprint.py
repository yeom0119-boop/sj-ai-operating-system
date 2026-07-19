"""Tests for preliminary institutional-footprint scoring."""

import unittest

import pandas as pd

from modules.footprint import calculate_footprint_scores
from modules.market_data import calculate_indicators


class FootprintScoreTests(unittest.TestCase):
    """Verify weighted Money In and Money Out score behavior."""

    def test_strong_rising_data_produces_high_money_in_score(self) -> None:
        """Rising prices, OBV, and strong volume favor Money In."""
        data = pd.DataFrame(
            {
                "Close": list(range(1, 201)),
                "Volume": ([100] * 199) + [150],
            }
        )
        indicators = calculate_indicators(data)

        result = calculate_footprint_scores(indicators)

        self.assertEqual(result["money_in_score"], 85)
        self.assertEqual(result["money_out_score"], 0)

    def test_strong_falling_data_produces_high_money_out_score(self) -> None:
        """Falling prices, OBV, weak RSI, and strong volume favor Money Out."""
        data = pd.DataFrame(
            {
                "Close": list(range(200, 0, -1)),
                "Volume": ([100] * 199) + [150],
            }
        )
        indicators = calculate_indicators(data)

        result = calculate_footprint_scores(indicators)

        self.assertEqual(result["money_in_score"], 0)
        self.assertEqual(result["money_out_score"], 100)


if __name__ == "__main__":
    unittest.main()