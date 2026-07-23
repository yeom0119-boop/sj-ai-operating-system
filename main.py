"""SJ AI Operating System v2.0 command-line menu."""

import sys
from modules.ai_analyzer import analyze_sec_guidance
from modules.market_data import build_stock_report
from modules.market_scanner import (
    load_market_scanner_config,
    rank_technical_candidates,
    scan_us_market_technical_candidates,
)
from modules.options_data import build_options_report
from modules.institutional_footprint import build_footprint_report
from modules.watchlist import (
    add_to_watchlist,
    load_watchlist,
    remove_from_watchlist,
)
from modules.sec_filings import (
    build_earnings_guidance_report,
    build_filing_content_report,
    build_sec_filings_report,
)
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
    """Print the v2.0 main menu."""
    print()
    print("=========================")
    print("SJ AI Operating System v2.0")
    print("=========================")
    print("1. Create daily note")
    print("2. Create stock note")
    print("3. Read stock note")
    print("4. List stock notes")
    print("5. Add stock analysis")
    print("6. Search all notes")
    print("7. List recent notes")
    print("8. Generate automated stock report")
    print("9. Generate official SEC filings report")
    print("10. Generate Gemini SEC guidance analysis")
    print("11. List watchlist")
    print("12. Add stock to watchlist")
    print("13. Remove stock from watchlist")
    print("14. Generate reports for all watchlist stocks")
    print("15. Generate integrated analysis for all watchlist stocks")
    print("16. Generate options reports for all watchlist stocks")
    print("17. Generate footprint radar for all watchlist stocks")
    print("18. Run full U.S. Market Scanner")
    print("19. Exit")
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
    

def handle_generate_sec_report() -> None:
    """Download official SEC filing links and append them to a stock note."""
    ticker = input("Enter stock ticker: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    print("\nDownloading official SEC filings...")

    try:
        metadata_report = build_sec_filings_report(ticker)
        content_report = build_filing_content_report(ticker)
        guidance_report = build_earnings_guidance_report(ticker)
        report = f"{metadata_report}\n\n{content_report}\n\n{guidance_report}"
        saved_path, action = save_stock_note(ticker, report)
    except Exception as error:
        # Keep the menu available when SEC access or configuration fails.
        print(f"\nError: SEC report could not be created: {error}")
        return

    print()
    if action == "create":
        print("Stock note created with official SEC filings.")
    else:
        print("Official SEC filings appended to stock note.")
    print(f"Location: {_relative_vault_path(saved_path)}")

def handle_generate_gemini_guidance_analysis() -> None:
    """Analyze official SEC earnings guidance with Gemini and save the result."""
    ticker = input("Enter stock ticker: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    print("\nAnalyzing official SEC guidance with Gemini...")

    try:
        current_report = build_earnings_guidance_report(ticker, release_index=0)
        previous_report = build_earnings_guidance_report(ticker, release_index=1)
        comparison_source = (
            f"# CURRENT EARNINGS GUIDANCE\n\n{current_report}"
            f"\n\n# PREVIOUS EARNINGS GUIDANCE\n\n{previous_report}"
        )
        analysis = analyze_sec_guidance(ticker, comparison_source)
        saved_path, action = save_stock_note(ticker, analysis)
    except Exception as error:
        # Keep the menu available when SEC or Gemini access fails.
        print(f"\nError: Gemini guidance analysis could not be created: {error}")
        return

    print()
    if action == "create":
        print("Stock note created with Gemini SEC guidance analysis.")
    else:
        print("Gemini SEC guidance analysis appended to stock note.")
    print(f"Location: {_relative_vault_path(saved_path)}")

def handle_list_watchlist() -> None:
    """Display every ticker registered in the watchlist."""
    try:
        tickers = load_watchlist()
    except ValueError as error:
        print(f"\nError: {error}")
        return

    print()
    if not tickers:
        print("Watchlist is empty.")
        return

    print(f"Watchlist ({len(tickers)} stocks):")
    for ticker in tickers:
        print(f"  - {ticker}")


def handle_add_watchlist() -> None:
    """Add a user-entered ticker to the persistent watchlist."""
    ticker = input("Enter stock ticker to add: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    try:
        normalized, added = add_to_watchlist(ticker)
    except ValueError as error:
        print(f"\nError: {error}")
        return

    print()
    if added:
        print(f"{normalized} added to watchlist.")
    else:
        print(f"{normalized} is already in watchlist.")


def handle_remove_watchlist() -> None:
    """Remove a user-entered ticker from the persistent watchlist."""
    ticker = input("Enter stock ticker to remove: ").strip()
    if not ticker:
        print("\nError: ticker cannot be empty.")
        return

    try:
        normalized, removed = remove_from_watchlist(ticker)
    except ValueError as error:
        print(f"\nError: {error}")
        return

    print()
    if removed:
        print(f"{normalized} removed from watchlist.")
    else:
        print(f"{normalized} was not found in watchlist.")
def handle_generate_watchlist_reports() -> None:
    """Generate automated market reports for every watchlist ticker.

    Input: tickers loaded from the persistent watchlist.
    Output: one saved stock report per ticker and a completion summary.
    Role: update all tracked stocks without repeated manual ticker entry.
    """
    try:
        tickers = load_watchlist()
    except ValueError as error:
        print(f"\nError: {error}")
        return

    if not tickers:
        print("\nWatchlist is empty.")
        return

    print(f"\nGenerating reports for {len(tickers)} watchlist stocks...")

    completed = []
    failed = []

    for position, ticker in enumerate(tickers, start=1):
        print(f"\n[{position}/{len(tickers)}] Processing {ticker}...")

        try:
            report = build_stock_report(ticker)
            saved_path, _action = save_stock_note(ticker, report)
        except Exception as error:
            # Continue processing other stocks when one provider request fails.
            failed.append((ticker, str(error)))
            print(f"Error: {ticker} report could not be created: {error}")
            continue

        completed.append(ticker)
        print(f"Saved: {_relative_vault_path(saved_path)}")

    print("\nWatchlist report generation completed.")
    print(f"Successful: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed tickers:")
        for ticker, error_message in failed:
            print(f"  - {ticker}: {error_message}")
def handle_generate_watchlist_options_reports() -> None:
    """Generate options reports for every watchlist ticker.

    Input: tickers loaded from the persistent watchlist.
    Output: one options-footprint report per ticker.
    Role: update options positioning without running paid AI analysis.
    """
    try:
        tickers = load_watchlist()
    except ValueError as error:
        print(f"\nError: {error}")
        return

    if not tickers:
        print("\nWatchlist is empty.")
        return

    print(f"\nGenerating options reports for {len(tickers)} stocks...")

    completed = []
    failed = []

    for position, ticker in enumerate(tickers, start=1):
        print(f"\n[{position}/{len(tickers)}] Processing {ticker} options...")

        try:
            report = build_options_report(ticker)
            saved_path, _action = save_stock_note(ticker, report)
        except Exception as error:
            # Continue when one ticker has no options or provider data fails.
            failed.append((ticker, str(error)))
            print(f"Error: {ticker} options report failed: {error}")
            continue

        completed.append(ticker)
        print(f"Saved: {_relative_vault_path(saved_path)}")

    print("\nWatchlist options report generation completed.")
    print(f"Successful: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed tickers:")
        for ticker, error_message in failed:
            print(f"  - {ticker}: {error_message}")

def handle_generate_watchlist_footprint_reports() -> None:
    """Generate footprint-radar reports for every watchlist ticker.

    Input: tickers loaded from the persistent watchlist.
    Output: one Money In/Out report saved to each stock note.
    Role: update probability-based institutional-footprint signals.
    """
    try:
        tickers = load_watchlist()
    except ValueError as error:
        print(f"\nError: {error}")
        return

    if not tickers:
        print("\nWatchlist is empty.")
        return

    print(f"\nGenerating footprint reports for {len(tickers)} stocks...")

    completed = []
    failed = []

    for position, ticker in enumerate(tickers, start=1):
        print(f"\n[{position}/{len(tickers)}] Processing {ticker} footprint...")

        try:
            report = build_footprint_report(ticker)
            saved_path, _action = save_stock_note(ticker, report)
        except Exception as error:
            # Continue so one provider failure does not stop the watchlist.
            failed.append((ticker, str(error)))
            print(f"Error: {ticker} footprint report failed: {error}")
            continue

        completed.append(ticker)
        print(f"Saved: {_relative_vault_path(saved_path)}")

    print("\nWatchlist footprint report generation completed.")
    print(f"Successful: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed tickers:")
        for ticker, error_message in failed:
            print(f"  - {ticker}: {error_message}")


def handle_generate_watchlist_integrated_analysis() -> None:
    """Generate integrated analysis for every watchlist ticker.

    Input: tickers loaded from the persistent watchlist.
    Output: market data, SEC guidance comparison, and Gemini analysis.
    Role: run the existing research pipeline for all tracked stocks.
    """
    try:
        tickers = load_watchlist()
    except ValueError as error:
        print(f"\nError: {error}")
        return

    if not tickers:
        print("\nWatchlist is empty.")
        return

    print(
        f"\nGenerating integrated analysis for "
        f"{len(tickers)} watchlist stocks..."
    )

    completed = []
    failed = []

    for position, ticker in enumerate(tickers, start=1):
        print(f"\n[{position}/{len(tickers)}] Processing {ticker}...")

        try:
            print("  1/4 Downloading market data...")
            market_report = build_stock_report(ticker)

            print("  2/4 Downloading options data...")
            options_report = build_options_report(ticker)

            print("  3/4 Downloading current and previous SEC guidance...")           
            current_guidance = build_earnings_guidance_report(
                ticker,
                release_index=0,
            )
            previous_guidance = build_earnings_guidance_report(
                ticker,
                release_index=1,
            )

            comparison_source = (
                f"# CURRENT EARNINGS GUIDANCE\n\n{current_guidance}"
                f"\n\n# PREVIOUS EARNINGS GUIDANCE\n\n{previous_guidance}"
            )

            print("  4/4 Analyzing SEC guidance with Gemini...")
            gemini_analysis = analyze_sec_guidance(
                ticker,
                comparison_source,
            )

            integrated_report = (
                "# Integrated Watchlist Analysis\n\n"
                f"{market_report}\n\n"
                "---\n\n"
                "## Options Footprint\n\n"
                f"{options_report}\n\n"
                "---\n\n"
                "## Current SEC Guidance\n\n"
                f"{current_guidance}\n\n"
                "---\n\n"
                "## Previous SEC Guidance\n\n"
                f"{previous_guidance}\n\n"
                "---\n\n"
                "## Gemini Guidance Comparison\n\n"
                f"{gemini_analysis}"
            )

            saved_path, _action = save_stock_note(
                ticker,
                integrated_report,
            )
        except Exception as error:
            # Preserve batch progress when one stock or provider fails.
            failed.append((ticker, str(error)))
            print(f"Error: {ticker} integrated analysis failed: {error}")
            continue

        completed.append(ticker)
        print(f"Saved: {_relative_vault_path(saved_path)}")

    print("\nIntegrated watchlist analysis completed.")
    print(f"Successful: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed tickers:")
        for ticker, error_message in failed:
            print(f"  - {ticker}: {error_message}")


def handle_scan_us_market() -> None:
    """Run the configured full-market liquidity and technical scan.

    Input: scanner thresholds loaded from config/market_scanner.json.
    Output: qualifying ticker symbols and their core technical signals.
    Role: expose the v2.0 Market Scanner through the main menu.
    """
    try:
        config = load_market_scanner_config()

        print("\nStarting full U.S. market scan...")
        print("This may take several minutes.")

        filtered_candidates = scan_us_market_technical_candidates(
            min_price=float(config["min_price"]),
            min_average_volume=int(config["min_average_volume"]),
            min_average_dollar_volume=float(
                config["min_average_dollar_volume"]
            ),
            min_rsi=float(config["min_rsi"]),
            require_above_ma20=bool(config["require_above_ma20"]),
            require_rising_obv=bool(config["require_rising_obv"]),
            require_rising_ad=bool(config["require_rising_ad"]),
            batch_size=int(config["batch_size"]),
        )
        candidates = rank_technical_candidates(
            filtered_candidates,
            max_candidates=int(config["max_candidates"]),
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"\nError: {error}")
        return
    except Exception as error:
        # Keep the main menu available when a market provider fails.
        print(f"\nError: market scan failed: {error}")
        return

    print("\nMarket scan completed.")
    print(f"Candidates: {len(candidates)}")

    if not candidates:
        print("No stocks passed every configured filter.")
        return

    print("\nQualified stocks:")
    for position, candidate in enumerate(candidates, start=1):
        print(
            f"{position}. {candidate['ticker']} | "
            f"Price: ${candidate['price']:.2f} | "
            f"RSI14: {candidate['rsi14']:.2f}"
        )

def main() -> None:
    """Run the SJ AI Operating System v2.0 interactive menu."""
    _configure_stdout()
    while True:
        print_menu()
        try:
            choice = input("Select (1-19): ").strip()
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
            handle_generate_sec_report()
        elif choice == "10":
            handle_generate_gemini_guidance_analysis()
        elif choice == "11":
            handle_list_watchlist()
        elif choice == "12":
            handle_add_watchlist()
        elif choice == "13":
            handle_remove_watchlist()
        elif choice == "14":
            handle_generate_watchlist_reports()
        elif choice == "15":
            handle_generate_watchlist_integrated_analysis()
        elif choice == "16":
            handle_generate_watchlist_options_reports()
        elif choice == "17":
            handle_generate_watchlist_footprint_reports()
        elif choice == "18":
            handle_scan_us_market()
        elif choice == "19":
            print("\nGoodbye.")
            break
        else:
            print("\nError: please enter a number from 1 to 19.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting.")
