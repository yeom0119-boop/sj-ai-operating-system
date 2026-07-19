"""Collect official company filing metadata from the SEC EDGAR API."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Iterable

import requests
from bs4 import BeautifulSoup


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
    
    
def download_filing_text(document_url: str) -> str:
    """Download and clean the visible text of an official SEC filing.

    Input:
        document_url: A document URL created from SEC filing metadata.
    Output:
        Plain text extracted from the filing HTML.
    Role:
        Prepare official filing content for keyword search and later AI analysis.
    """
    allowed_prefix = f"{SEC_ARCHIVES_URL}/"
    if not document_url.startswith(allowed_prefix):
        raise ValueError("Only official SEC Archives document URLs are allowed.")

    headers = {
        "User-Agent": get_sec_user_agent(),
        "Accept-Encoding": "gzip, deflate",
    }
    response = requests.get(document_url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    hidden_xbrl_tags = {
        "ix:hidden",
        "ix:header",
        "ix:references",
        "ix:resources",
        "xbrli:context",
        "xbrli:unit",
    }
    for element in soup.find_all(hidden_xbrl_tags):
        element.decompose()    

    text = " ".join(soup.stripped_strings)
    cleaned_text = re.sub(r"\s+", " ", text).strip()

    if not cleaned_text:
        raise RuntimeError("The SEC filing contained no readable text.")

    return cleaned_text


def find_keyword_excerpts(
    filing_text: str,
    keywords: Iterable[str] = (
        "guidance",
        "outlook",
        "expects",
        "forecast",
        "revenue",
        "gross margin",
        "demand",
        "supply",
    ),
    context_chars: int = 280,
    max_excerpts: int = 8,
) -> list[dict[str, str]]:
    """Find short filing excerpts around important business keywords.

    Input:
        filing_text: Clean official filing text.
        keywords: Terms related to guidance, earnings, and business conditions.
        context_chars: Text length retained before and after a keyword.
        max_excerpts: Maximum number of excerpts.
    Output:
        Keyword and excerpt dictionaries.
    Role:
        Narrow large filings to primary-source passages worth reviewing.
    """
    if not filing_text.strip():
        return []

    lowered_text = filing_text.lower()
    results: list[dict[str, str]] = []
    used_ranges: list[tuple[int, int]] = []

    for keyword in keywords:
        for match in re.finditer(re.escape(keyword.lower()), lowered_text):
            start = max(0, match.start() - context_chars)
            end = min(len(filing_text), match.end() + context_chars)

            if any(start < used_end and end > used_start for used_start, used_end in used_ranges):
                continue

            excerpt = filing_text[start:end].strip()
            if start > 0:
                excerpt = f"...{excerpt}"
            if end < len(filing_text):
                excerpt = f"{excerpt}..."

            results.append(
                {
                    "keyword": keyword,
                    "excerpt": excerpt,
                }
            )
            used_ranges.append((start, end))

            if len(results) >= max_excerpts:
                return results

    return results


def build_filing_content_report(
    ticker: str,
    form_type: str = "10-Q",
) -> str:
    """Create an Obsidian report from the latest selected SEC filing.

    Input:
        ticker: A U.S. stock ticker.
        form_type: SEC form to inspect, such as 10-Q, 10-K, or 8-K.
    Output:
        Markdown containing filing facts and keyword excerpts.
    Role:
        Surface official filing evidence without presenting AI conclusions as facts.
    """
    filings = get_recent_filings(ticker, forms=(form_type,), limit=1)
    if not filings:
        raise RuntimeError(f"No recent {form_type} filing found for {ticker.upper()}.")

    filing = filings[0]
    filing_text = download_filing_text(filing["document_url"])
    excerpts = find_keyword_excerpts(filing_text)

    lines = [
        f"## Official SEC {form_type} Content Review",
        "",
        "### Confirmed filing facts",
        "",
        f"- Ticker: {filing['ticker']}",
        f"- Company: {filing['company_name']}",
        f"- Filing date: {filing['filing_date']}",
        f"- Report date: {filing['report_date']}",
        f"- Form: {filing['form']}",
        f"- [Official SEC document]({filing['document_url']})",
        "",
        "### Keyword excerpts from the official filing",
        "",
    ]

    if not excerpts:
        lines.append("- No configured keywords were found.")
    else:
        for item in excerpts:
            lines.extend(
                [
                    f"#### Keyword: {item['keyword']}",
                    "",
                    item["excerpt"],
                    "",
                ]
            )

    lines.extend(
        [
            "### Interpretation boundary",
            "",
            "- Excerpts are copied from the official filing text.",
            "- Keyword matching does not determine whether guidance is bullish or bearish.",
            "- Final interpretation must compare the full document, prior guidance, and current results.",
        ]
    )

    return "\n".join(lines)