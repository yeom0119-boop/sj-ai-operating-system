"""
SJ AI Operating System
modules/obsidian.py

Obsidian-compatible vault operations for local Markdown notes.

Role:
- Create daily notes under vault/Daily/
- Create stock notes under vault/Stocks/
- Read stock notes and list saved tickers
- Search the vault recursively by filename and content
- List the most recently modified Markdown notes
- Preserve legacy stock-note save helper used by earlier versions

TODO:
- YAML front matter for daily and stock notes
- Full-text search ranking and snippet highlighting
- AI-generated summaries appended to daily notes
- Configurable vault path via environment variable or settings file
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

# Characters that are invalid in Windows file names
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def get_vault_root() -> Path:
    """
    Return the Obsidian vault root directory.

    Output:
        Absolute path to the project's vault/ folder.
    """

    project_root = Path(__file__).resolve().parent.parent
    return project_root / "vault"


def _get_daily_folder() -> Path:
    """Return the vault/Daily/ folder path."""

    return get_vault_root() / "Daily"


def _get_stocks_folder() -> Path:
    """Return the vault/Stocks/ folder path."""

    return get_vault_root() / "Stocks"


def sanitize_stock_name(stock: str) -> str:
    """
    Normalize a stock ticker for safe use as a file name.

    Input:
        stock: Raw ticker or stock name from user input.

    Output:
        Uppercase, filesystem-safe ticker string.

    Raises:
        ValueError: When the cleaned name is empty.
    """

    cleaned = stock.strip().upper()

    for char in _INVALID_FILENAME_CHARS:
        cleaned = cleaned.replace(char, "")

    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError("Stock ticker is empty or cannot be used as a file name.")

    return cleaned


def _iter_markdown_files(root: Path) -> list[Path]:
    """
    Collect all Markdown files under a directory tree.

    Input:
        root: Vault root or subdirectory to scan.

    Output:
        List of .md file paths (files only, sorted for stable results).
    """

    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file()
    )


def create_daily_note(note_date: date | None = None) -> tuple[Path, str]:
    """
    Create a daily note for the given date (today by default).

    Input:
        note_date: Calendar date for the note; defaults to today.

    Output:
        Tuple of (file path, action) where action is "create" or "exists".

    Side effects:
        Creates vault/Daily/ when missing. Does not overwrite existing notes.
    """

    target_date = note_date or date.today()
    daily_folder = _get_daily_folder()
    daily_folder.mkdir(parents=True, exist_ok=True)

    filename = f"{target_date.isoformat()}.md"
    file_path = daily_folder / filename

    if file_path.exists():
        return file_path, "exists"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown = f"""# Daily Note — {target_date.isoformat()}

- Created: {created_at}
- Project: SJ AI Operating System v0.2

## Notes

"""

    file_path.write_text(markdown, encoding="utf-8")
    return file_path, "create"


def create_stock_note(ticker: str, content: str = "") -> tuple[Path, str]:
    """
    Create a stock note for an uppercase ticker.

    Input:
        ticker: Stock ticker symbol (converted to uppercase).
        content: Optional initial note body.

    Output:
        Tuple of (file path, action) where action is "create" or "exists".

    Side effects:
        Creates vault/Stocks/ when missing. Does not overwrite existing notes.
    """

    stocks_folder = _get_stocks_folder()
    stocks_folder.mkdir(parents=True, exist_ok=True)

    clean_ticker = sanitize_stock_name(ticker)
    file_path = stocks_folder / f"{clean_ticker}.md"

    if file_path.exists():
        return file_path, "exists"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = content.strip() or "Add your analysis here."

    markdown = f"""# {clean_ticker}

## Basic Info

- Ticker: {clean_ticker}
- Created: {created_at}
- Project: SJ AI Operating System v0.2

## Analysis

{body}
"""

    file_path.write_text(markdown, encoding="utf-8")
    return file_path, "create"


def search_vault(query: str) -> list[dict[str, object]]:
    """
    Search all Markdown files in the vault by filename and content.

    Input:
        query: Case-insensitive search term.

    Output:
        List of match dictionaries with keys:
            - path: Absolute Path to the note
            - relative_path: Path relative to the vault root
            - filename_match: True when the query matches the file name
            - content_match: True when the query appears in file contents
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        return []

    vault_root = get_vault_root()
    needle = cleaned_query.casefold()
    results: list[dict[str, object]] = []

    for file_path in _iter_markdown_files(vault_root):
        filename_match = needle in file_path.name.casefold()
        content_match = False

        try:
            file_text = file_path.read_text(encoding="utf-8")
        except OSError:
            # Skip unreadable files instead of failing the whole search.
            continue

        content_match = needle in file_text.casefold()

        if filename_match or content_match:
            results.append(
                {
                    "path": file_path,
                    "relative_path": file_path.relative_to(vault_root),
                    "filename_match": filename_match,
                    "content_match": content_match,
                }
            )

    return results


def list_recent_notes(limit: int = 10) -> list[tuple[Path, datetime]]:
    """
    List the most recently modified Markdown notes in the vault.

    Input:
        limit: Maximum number of notes to return (default 10).

    Output:
        List of (absolute path, last modified datetime) sorted newest first.
    """

    vault_root = get_vault_root()
    markdown_files = _iter_markdown_files(vault_root)

    dated_files: list[tuple[Path, datetime]] = []

    for file_path in markdown_files:
        try:
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        except OSError:
            continue

        dated_files.append((file_path, modified))

    # Newest modification time first
    dated_files.sort(key=lambda item: item[1], reverse=True)
    return dated_files[:limit]


def list_stock_notes() -> list[str]:
    """
    List all saved stock note tickers in alphabetical order.

    Output:
        List of uppercase .md file stems in vault/Stocks/.
    """

    stocks_folder = _get_stocks_folder()

    if not stocks_folder.exists():
        return []

    names = [
        path.stem
        for path in stocks_folder.glob("*.md")
        if path.is_file()
    ]

    return sorted(names)


def read_stock_note(symbol: str) -> str:
    """
    Read a stock note's full Markdown content.

    Input:
        symbol: Stock ticker symbol (converted to uppercase).

    Output:
        Full note text, or an empty string when the note does not exist.

    Raises:
        ValueError: When the symbol is empty or invalid.
    """

    clean_stock = sanitize_stock_name(symbol)
    file_path = _get_stocks_folder() / f"{clean_stock}.md"

    if not file_path.exists():
        return ""

    return file_path.read_text(encoding="utf-8")


def save_stock_note(stock: str, content: str) -> tuple[Path, str]:
    """
    Append analysis to an existing stock note or create a new one (legacy helper).

    Input:
        stock: Ticker or stock name.
        content: Analysis text to store.

    Output:
        Tuple of (file path, action) where action is "create" or "append".
    """

    stocks_folder = _get_stocks_folder()
    stocks_folder.mkdir(parents=True, exist_ok=True)

    clean_stock = sanitize_stock_name(stock)
    file_path = stocks_folder / f"{clean_stock}.md"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_entry = f"""
---

## Analysis Entry — {created_at}

{content}
"""

    if file_path.exists():
        # Keep prior entries and append the new analysis block.
        with file_path.open("a", encoding="utf-8") as file:
            file.write(new_entry)

        return file_path, "append"

    markdown = f"""# {clean_stock}

## Basic Info

- Ticker: {clean_stock}
- Created: {created_at}
- Project: SJ AI Operating System

## Analysis Entry — {created_at}

{content}
"""

    file_path.write_text(markdown, encoding="utf-8")
    return file_path, "create"
