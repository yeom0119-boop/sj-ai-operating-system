"""Collect official company filing metadata from the SEC EDGAR API."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable

import requests


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"


def get_sec_user_agent() -> str:
    """Read the locally configured SEC identification string.

    Output:
        A User-Agent containing the project name and contact email.
    Role:
        Follow SEC automated-access requirements without committing private email.
    """
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise RuntimeError(
            "SEC_USER_AGENT is not configured. "
            "Set it to 'SJ AI Operating System your-email@example.com'."
        )
    return user_agent


def _download_json(url: str) -> dict:
    """Download JSON from an official SEC endpoint.

    Input:
        url: An SEC HTTPS JSON endpoint.
    Output:
        Parsed JSON dictionary.
    Role:
        Apply consistent identification, timeout, and error handling.
    """
    headers = {
        "User-Agent": get_sec_user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def get_company_ticker_map() -> dict:
    """Download and cache the SEC ticker-to-CIK reference data."""
    return _download_json(SEC_TICKERS_URL)


def lookup_company(ticker: str) -> dict[str, object]:
    """Find an SEC company name and CIK from a stock ticker.

    Input:
        ticker: A U.S. stock ticker such as NVDA or MSFT.
    Output:
        Dictionary containing ticker, company name, and ten-digit CIK.
    Role:
        Resolve user tickers before requesting official company submissions.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker cannot be empty.")

    for company in get_company_ticker_map().values():
        if str(company.get("ticker", "")).upper() == symbol:
            cik = str(company["cik_str"]).zfill(10)
            return {
                "ticker": symbol,
                "company_name": company["title"],
                "cik": cik,
            }

    raise ValueError(f"No SEC company found for ticker {symbol}.")


def get_recent_filings(
    ticker: str,
    forms: Iterable[str] = ("10-K", "10-Q", "8-K"),
    limit: int = 10,
) -> list[dict[str, str]]:
    """Return recent official SEC filings for a ticker.

    Input:
        ticker: A U.S. stock ticker.
        forms: Filing types to include.
        limit: Maximum number of results.
    Output:
        Filing metadata with official SEC document links.
    Role:
        Provide primary-source company documents for later AI analysis.
    """
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    company = lookup_company(ticker)
    cik = str(company["cik"])
    submissions = _download_json(SEC_SUBMISSIONS_URL.format(cik=cik))
    recent = submissions.get("filings", {}).get("recent", {})
    allowed_forms = set(forms)
    results: list[dict[str, str]] = []

    accession_numbers = recent.get("accessionNumber", [])
    for index, accession_number in enumerate(accession_numbers):
        form = recent.get("form", [])[index]
        if form not in allowed_forms:
            continue

        primary_document = recent.get("primaryDocument", [])[index]
        accession_compact = accession_number.replace("-", "")
        cik_compact = str(int(cik))
        document_url = (
            f"{SEC_ARCHIVES_URL}/{cik_compact}/"
            f"{accession_compact}/{primary_document}"
        )

        results.append(
            {
                "ticker": str(company["ticker"]),
                "company_name": str(company["company_name"]),
                "cik": cik,
                "form": form,
                "filing_date": recent.get("filingDate", [])[index],
                "report_date": recent.get("reportDate", [])[index],
                "accession_number": accession_number,
                "primary_document": primary_document,
                "document_url": document_url,
            }
        )

        if len(results) >= limit:
            break

    return results


def build_sec_filings_report(ticker: str, limit: int = 10) -> str:
    """Create an Obsidian-ready Markdown list of official SEC filings."""
    company = lookup_company(ticker)
    filings = get_recent_filings(ticker, limit=limit)

    lines = [
        "## Official SEC Filings",
        "",
        "### Confirmed facts",
        "",
        f"- Ticker: {company['ticker']}",
        f"- Company: {company['company_name']}",
        f"- SEC CIK: {company['cik']}",
        "- Source: U.S. Securities and Exchange Commission EDGAR",
        "",
        "### Recent filings",
        "",
    ]

    if not filings:
        lines.append("- No matching 10-K, 10-Q, or 8-K filings found.")
    else:
        for filing in filings:
            lines.append(
                f"- {filing['filing_date']} | {filing['form']} | "
                f"[Official document]({filing['document_url']})"
            )

    lines.extend(
        [
            "",
            "### Analysis rule",
            "",
            "- SEC filing metadata is a confirmed primary-source fact.",
            "- Filing contents require separate extraction and interpretation.",
            "- Company guidance must be checked against the original document.",
        ]
    )

    return "\n".join(lines)