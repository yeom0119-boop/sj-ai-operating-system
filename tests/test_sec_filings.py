"""Tests for official SEC filing metadata collection."""

import unittest
from unittest.mock import patch

from modules.sec_filings import (
    build_sec_filings_report,
    get_recent_filings,
    lookup_company,
)


class SecFilingsTests(unittest.TestCase):
    """Verify SEC ticker lookup, filing filtering, and Markdown output."""

    def test_lookup_company_returns_ten_digit_cik(self) -> None:
        """Ticker lookup returns normalized ticker, company name, and padded CIK."""
        ticker_map = {
            "0": {
                "cik_str": 1045810,
                "ticker": "NVDA",
                "title": "NVIDIA CORP",
            }
        }

        with patch(
            "modules.sec_filings.get_company_ticker_map",
            return_value=ticker_map,
        ):
            result = lookup_company(" nvda ")

        self.assertEqual(result["ticker"], "NVDA")
        self.assertEqual(result["company_name"], "NVIDIA CORP")
        self.assertEqual(result["cik"], "0001045810")

    def test_get_recent_filings_filters_supported_forms(self) -> None:
        """Only requested filing forms are returned with official document URLs."""
        company = {
            "ticker": "NVDA",
            "company_name": "NVIDIA CORP",
            "cik": "0001045810",
        }
        submissions = {
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0001045810-26-000060",
                        "0001045810-26-000052",
                        "0001045810-26-000040",
                    ],
                    "form": ["8-K", "10-Q", "4"],
                    "primaryDocument": [
                        "nvda-20260628.htm",
                        "nvda-20260426.htm",
                        "ownership.xml",
                    ],
                    "filingDate": [
                        "2026-07-02",
                        "2026-05-20",
                        "2026-04-01",
                    ],
                    "reportDate": [
                        "2026-06-28",
                        "2026-04-26",
                        "2026-04-01",
                    ],
                }
            }
        }

        with patch("modules.sec_filings.lookup_company", return_value=company):
            with patch(
                "modules.sec_filings._download_json",
                return_value=submissions,
            ):
                results = get_recent_filings("NVDA")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["form"], "8-K")
        self.assertEqual(results[1]["form"], "10-Q")
        self.assertIn("sec.gov/Archives/edgar/data", results[0]["document_url"])

    def test_build_report_marks_sec_as_primary_source(self) -> None:
        """Markdown output identifies SEC data as confirmed primary-source facts."""
        company = {
            "ticker": "NVDA",
            "company_name": "NVIDIA CORP",
            "cik": "0001045810",
        }
        filing = {
            "ticker": "NVDA",
            "company_name": "NVIDIA CORP",
            "cik": "0001045810",
            "form": "10-Q",
            "filing_date": "2026-05-20",
            "report_date": "2026-04-26",
            "accession_number": "0001045810-26-000052",
            "primary_document": "nvda-20260426.htm",
            "document_url": "https://www.sec.gov/example.htm",
        }

        with patch("modules.sec_filings.lookup_company", return_value=company):
            with patch(
                "modules.sec_filings.get_recent_filings",
                return_value=[filing],
            ):
                report = build_sec_filings_report("NVDA")

        self.assertIn("Official SEC Filings", report)
        self.assertIn("confirmed primary-source fact", report)
        self.assertIn("[Official document]", report)


if __name__ == "__main__":
    unittest.main()