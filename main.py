"""SJ AI Operating System v0.5 command-line menu."""

import sys
from modules.market_data import build_stock_report
from modules.obsidian import (
    create_daily_note,
    create_stock_note,
    get_vault_root,
    list_recent_notes,
    list_stock_notes,
    read_stock_note,
    save_stock_note,
    search_vault,
)


def _configure_stdout() -> None:
    """Ensure UTF-8 output on Windows consoles when supported."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def print_menu() -> None:
    """Print the v0.7 main menu."""
    print()
    print("=========================")
    print("SJ AI Operating System v0.7")
    print("=========================")
    print("1. Create daily note")
    print("2. Create stock note")
    print("3. Read stock note")
    print("4. List stock notes")
    print("5. Add stock analysis")
    print("6. Search all notes")
    print("7. List recent notes")
    print("8. Generate automated stock report")
    print("9. Exit")
    print()


def _relative_vault_path(file_path) -> str:
    """Show vault-relative paths in user messages."""
    try:
        return str(file_path.relative_to(get_vault_root()))
    except ValueError:
        return str(file_path)


def handle_create_daily_note() -> None:
    """Create today's daily note under vault/Daily/."""
    saved_path, action = create_daily_note()
    print()
    print("Daily note created." if action == "create" else "Daily note already exists.")
    print(f"Location: {_relative_vault_path(saved_path)}")


def handle_create_stock_note() -> None:
    """Create a stock note with an uppercase ticker."""
    ticker = input("Enter stock ticker: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return
    try:
        saved_path, action = create_stock_note(ticker)
    except ValueError as error:
        print(f"\nError: {error}")
        return
    print()
    print("Stock note created." if action == "create" else "Stock note already exists.")
    print(f"Location: {_relative_vault_path(saved_path)}")


def handle_read_stock_note() -> None:
    """Read and display a stock note by ticker symbol."""
    symbol = input("Enter stock ticker: ").strip()
    if not symbol:
        print("\nError: ticker cannot be empty.")
        return
    try:
        note_text = read_stock_note(symbol)
    except ValueError as error:
        print(f"\nError: {error}")
        return
    print()
    print(note_text if note_text else "No stock note found for that ticker.")


def handle_list_stock_notes() -> None:
    """List all saved stock note tickers."""
    notes = list_stock_notes()
    print()
    if not notes:
        print("No stock notes found.")
        return
    print("Saved stock notes:")
    for name in notes:
        print(f"  - {name}")


def handle_add_stock_analysis() -> None:
    """Append a timestamped analysis entry to a stock note."""
    ticker = input("Enter stock ticker: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    content = input("Enter analysis: ").strip()
    if not content:
        print("\nError: analysis cannot be empty.")
        return

    try:
        saved_path, action = save_stock_note(ticker, content)
    except ValueError as error:
        print(f"\nError: {error}")
        return

    print()
    if action == "create":
        print("Stock note created with analysis.")
    else:
        print("Analysis appended to stock note.")
    print(f"Location: {_relative_vault_path(saved_path)}")


def handle_search_vault() -> None:
    """Search every Markdown note by filename and content."""
    query = input("Enter search word: ").strip()
    if not query:
        print("\nError: search word cannot be empty.")
        return
    results = search_vault(query)
    print()
    if not results:
        print("No matching notes found.")
        return
    print(f"Search results ({len(results)}):")
    for result in results:
        match_types = []
        if result["filename_match"]:
            match_types.append("filename")
        if result["content_match"]:
            match_types.append("content")
        print(f"  - {result['relative_path']} [{', '.join(match_types)}]")


def handle_list_recent_notes() -> None:
    """List the ten most recently modified Markdown notes."""
    notes = list_recent_notes()
    print()
    if not notes:
        print("No notes found.")
        return
    print("Recent notes:")
    for file_path, modified in notes:
        relative_path = _relative_vault_path(file_path)
        print(f"  - {relative_path} ({modified:%Y-%m-%d %H:%M:%S})")




def handle_generate_stock_report() -> None:
    """Download market data and append an automated report to a stock note."""
    ticker = input("Enter stock ticker: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    print("\nDownloading market data...")

    try:
        report = build_stock_report(ticker)
        saved_path, action = save_stock_note(ticker, report)
    except Exception as error:
        # Keep the interactive menu running when internet or provider errors occur.
        print(f"\nError: market report could not be created: {error}")
        return

    print()
    if action == "create":
        print("Stock note created with automated market report.")
    else:
        print("Automated market report appended to stock note.")
    print(f"Location: {_relative_vault_path(saved_path)}")
    
def main() -> None:
    """Run the SJ AI Operating System v0.5 interactive menu."""
    _configure_stdout()
    while True:
        print_menu()
        try:
            choice = input("Select (1-9): ").strip()
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting.")
            break
        if choice == "1":
            handle_create_daily_note()
        elif choice == "2":
            handle_create_stock_note()
        elif choice == "3":
            try:
                handle_read_stock_note()
            except KeyboardInterrupt:
                print("\n\nRead cancelled.")
        elif choice == "4":
            handle_list_stock_notes()
        elif choice == "5":
            handle_add_stock_analysis()
        elif choice == "6":
            handle_search_vault()
        elif choice == "7":
            handle_list_recent_notes()
        elif choice == "8":
            handle_generate_stock_report()
        elif choice == "9":
            print("\nGoodbye.")
            break
        else:
            print("\nError: please enter a number from 1 to 9.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting.")
