"""Tests for the Gemini AI analysis adapter."""

import unittest
from unittest.mock import patch

from modules import ai_analyzer


class GeminiClientTests(unittest.TestCase):
    """Verify Gemini client authentication and network configuration."""

    @patch("modules.ai_analyzer.genai.Client")
    @patch("modules.ai_analyzer.os.getenv", return_value="test-api-key")
    @patch("modules.ai_analyzer.load_dotenv")
    def test_get_gemini_client_sets_timeout(
        self,
        mock_load_dotenv,
        mock_getenv,
        mock_client,
    ):
        """The Gemini client receives the API key and request timeout."""
        client = ai_analyzer.get_gemini_client()

        self.assertIs(client, mock_client.return_value)
        mock_load_dotenv.assert_called_once_with()
        mock_getenv.assert_called_once_with("GEMINI_API_KEY", "")

        client_options = mock_client.call_args.kwargs
        self.assertEqual(client_options["api_key"], "test-api-key")
        self.assertEqual(
            client_options["http_options"].timeout,
            ai_analyzer.GEMINI_TIMEOUT_MS,
        )


if __name__ == "__main__":
    unittest.main()