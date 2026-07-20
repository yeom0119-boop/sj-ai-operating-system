"""Manage the user-editable stock watchlist stored as local JSON."""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = PROJECT_ROOT / "config" / "watchlist.json"
TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,15}$")


def normalize_ticker(ticker: str) -> str:
    """Return a validated uppercase ticker symbol.

    Input: ticker entered by the user.
    Output: normalized uppercase ticker.
    Role: prevent empty or unsafe ticker values from entering the watchlist.
    """
    normalized = ticker.strip().upper()
    if not TICKER_PATTERN.fullmatch(normalized):
        raise ValueError(
            "ticker must contain only letters, numbers, dots, or hyphens"
        )
    return normalized


def load_watchlist() -> list[str]:
    """Load and return the saved ticker list.

    Input: none.
    Output: sorted list of ticker symbols.
    Role: safely read the local watchlist, returning an empty list if absent.
    """
    if not WATCHLIST_PATH.exists():
        return []

    try:
        saved_data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"watchlist could not be read: {error}") from error

    if not isinstance(saved_data, list):
        raise ValueError("watchlist data must be a JSON list")

    valid_tickers = []
    for ticker in saved_data:
        if isinstance(ticker, str):
            try:
                valid_tickers.append(normalize_ticker(ticker))
            except ValueError:
                # Ignore damaged individual entries while preserving valid ones.
                continue

    return sorted(set(valid_tickers))


def save_watchlist(tickers: list[str]) -> None:
    """Save a normalized ticker list to config/watchlist.json.

    Input: list of ticker symbols.
    Output: none.
    Role: create the config folder and persist the watchlist.
    """
    normalized = sorted({normalize_ticker(ticker) for ticker in tickers})
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_to_watchlist(ticker: str) -> tuple[str, bool]:
    """Add one ticker to the watchlist.

    Input: ticker symbol.
    Output: normalized ticker and True when newly added.
    Role: prevent duplicate entries.
    """
    normalized = normalize_ticker(ticker)
    tickers = load_watchlist()

    if normalized in tickers:
        return normalized, False

    tickers.append(normalized)
    save_watchlist(tickers)
    return normalized, True


def remove_from_watchlist(ticker: str) -> tuple[str, bool]:
    """Remove one ticker from the watchlist.

    Input: ticker symbol.
    Output: normalized ticker and True when removed.
    Role: safely handle requests for tickers that are not registered.
    """
    normalized = normalize_ticker(ticker)
    tickers = load_watchlist()

    if normalized not in tickers:
        return normalized, False

    tickers.remove(normalized)
    save_watchlist(tickers)
    return normalized, True


# TODO: Use this watchlist as the target list for future batch AI reports.