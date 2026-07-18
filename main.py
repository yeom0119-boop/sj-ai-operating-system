"""
SJ AI Operating System
main.py

Command-line entry point for the v0.2 Obsidian vault MVP.

Role:
- Display the interactive menu
- Route user choices to vault operations in modules/obsidian.py
- Handle invalid input and keyboard interruption without crashing

TODO:
- Command-line flags for non-interactive use (e.g. --daily, --search)
- Settings file for default vault location
- Richer prompts with multiline note input
"""

import sys

from modules.obsidian import (
    create_daily_note,
    create_stock_note,
    get_vault_root,
    list_recent_notes,
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
    """Print the v0.2 main menu."""

    print()
    print("=========================")
    print("SJ AI Operating System v0.2")
    print("=========================")
    print("1. Create daily note")
    print("2. Create stock note")
    print("3. Search vault")
    print("4. List recent notes")
    print("5. Exit")
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

    if action == "create":
        print("Daily note created.")
    else:
        print("Daily note already exists.")

    print(f"Location: {_relative_vault_path(saved_path)}")


def handle_create_stock_note() -> None:
    """Create a stock note with an uppercase ticker."""

    ticker = input("Enter stock ticker: ").strip()

    if not ticker:
        print()
        print("Error: ticker cannot be empty.")
        return

    try:
        saved_path, action = create_stock_note(ticker)
    except ValueError as error:
        print()
        print(f"Error: {error}")
        return

    print()

    if action == "create":
        print("Stock note created.")
    else:
        print("Stock note already exists.")

    print(f"Location: {_relative_vault_path(saved_path)}")


def handle_search_vault() -> None:
    """Search the vault by filename and file contents."""

    query = input("Enter search term: ").strip()

    if not query:
        print()
        print("Error: search term cannot be empty.")
        return

    results = search_vault(query)

    print()

    if not results:
        print("No matching notes found.")
        return

    print(f"Found {len(results)} matching note(s):")

    for match in results:
        relative_path = match["relative_path"]
        flags: list[str] = []

        if match["filename_match"]:
            flags.append("filename")
        if match["content_match"]:
            flags.append("content")

        flag_text = ", ".join(flags) if flags else "match"
        print(f"  - {relative_path} ({flag_text})")


def handle_list_recent_notes() -> None:
    """Show the 10 most recently modified Markdown notes."""

    recent_notes = list_recent_notes(limit=10)

    print()

    if not recent_notes:
        print("No Markdown notes found in the vault.")
        return

    print("10 most recently modified notes:")

    for file_path, modified_at in recent_notes:
        timestamp = modified_at.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  - {_relative_vault_path(file_path)}  [{timestamp}]")


def main() -> None:
    """Run the SJ AI Operating System v0.2 interactive menu."""

    _configure_stdout()

    while True:
        print_menu()

        try:
            choice = input("Select (1-5): ").strip()
        except KeyboardInterrupt:
            print()
            print()
            print("Interrupted. Exiting.")
            break

        if choice == "1":
            handle_create_daily_note()
        elif choice == "2":
            handle_create_stock_note()
        elif choice == "3":
            try:
                handle_search_vault()
            except KeyboardInterrupt:
                print()
                print()
                print("Search cancelled.")
        elif choice == "4":
            handle_list_recent_notes()
        elif choice == "5":
            print()
            print("Goodbye.")
            break
        else:
            print()
            print("Error: please enter a number from 1 to 5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("Interrupted. Exiting.")
