"""Collect and format stock-options data for institutional-footprint research."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


import yfinance as yf

from modules.watchlist import normalize_ticker


def _safe_number(value: Any) -> float:
    """Convert a provider value to a finite number.

    Input: number-like provider value.
    Output: finite float, or 0.0 when missing.
    Role: prevent NaN option fields from damaging calculations.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    return number if math.isfinite(number) else 0.0


def _safe_implied_volatility(value: Any) -> float | None:
    """Convert provider IV to a positive finite number or missing value.

    Input: implied-volatility value from the option provider.
    Output: positive finite float, or None when missing or invalid.
    Role: prevent unavailable IV from being reported as a real 0.0%.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number) or number < 0.001:
        return None

    return number


def _sum_column(frame: Any, column: str) -> float:
    """Return a safe numeric sum for one option-chain column."""
    if frame is None or frame.empty or column not in frame.columns:
        return 0.0

    return sum(_safe_number(value) for value in frame[column])


def _put_call_ratio(put_value: float, call_value: float) -> float | None:
    """Calculate a put/call ratio without dividing by zero."""
    if call_value <= 0:
        return None
    return put_value / call_value


def _highest_open_interest(frame: Any) -> dict[str, Any] | None:
    """Return the contract with the largest reported open interest."""
    if frame is None or frame.empty or "openInterest" not in frame.columns:
        return None

    best_contract = None
    best_open_interest = -1.0

    for _index, row in frame.iterrows():
        open_interest = _safe_number(row.get("openInterest"))
        if open_interest > best_open_interest:
            best_open_interest = open_interest
            best_contract = {
                "contract": str(row.get("contractSymbol", "")),
                "strike": _safe_number(row.get("strike")),
                "open_interest": open_interest,
                "volume": _safe_number(row.get("volume")),
                "implied_volatility": _safe_implied_volatility(
                    row.get("impliedVolatility")
                ),
            }

    return best_contract


def _top_volume_oi_activity(
    frame: Any,
    option_type: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return contracts with the largest volume-to-OI ratios.

    Input: option-chain table, Call/Put label, and result limit.
    Output: ranked contract dictionaries.
    Role: surface unusual activity candidates without claiming institution identity.
    """
    if frame is None or frame.empty:
        return []

    candidates = []

    for _index, row in frame.iterrows():
        open_interest = _safe_number(row.get("openInterest"))
        volume = _safe_number(row.get("volume"))

        # OI must exist because zero-OI contracts create meaningless ratios.
        if open_interest < 1 or volume < 1:
            continue

        candidates.append(
            {
                "type": option_type,
                "contract": str(row.get("contractSymbol", "")),
                "strike": _safe_number(row.get("strike")),
                "open_interest": open_interest,
                "volume": volume,
                "volume_oi_ratio": volume / open_interest,
                "implied_volatility": _safe_implied_volatility(
                    row.get("impliedVolatility")
                ),
            }
        )

    candidates.sort(
        key=lambda item: (
            item["volume_oi_ratio"],
            item["volume"],
        ),
        reverse=True,
    )
    return candidates[:limit]


def collect_options_snapshot(
    ticker: str,
    expiration_limit: int = 3,
) -> dict[str, Any]:
    """Collect option-chain summaries for the nearest expirations.

    Input: ticker and number of expirations.
    Output: normalized option snapshot dictionary.
    Role: provide reusable raw inputs for future footprint scoring.
    """
    if expiration_limit < 1:
        raise ValueError("expiration_limit must be at least 1")

    normalized = normalize_ticker(ticker)
    stock = yf.Ticker(normalized)
    expirations = list(stock.options)

    if not expirations:
        raise ValueError(f"no listed options were found for {normalized}")

    price_history = stock.history(period="5d", auto_adjust=False)
    if price_history.empty:
        raise ValueError(f"current price could not be found for {normalized}")

    current_price = _safe_number(price_history["Close"].iloc[-1])
    collected_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    selected_expirations = expirations[:expiration_limit]
    expiration_reports = []

    for expiration in selected_expirations:
        chain = stock.option_chain(expiration)
        calls = chain.calls
        puts = chain.puts

        call_open_interest = _sum_column(calls, "openInterest")
        put_open_interest = _sum_column(puts, "openInterest")
        call_volume = _sum_column(calls, "volume")
        put_volume = _sum_column(puts, "volume")

        unusual_candidates = (
            _top_volume_oi_activity(calls, "Call")
            + _top_volume_oi_activity(puts, "Put")
        )
        unusual_candidates.sort(
            key=lambda item: (
                item["volume_oi_ratio"],
                item["volume"],
            ),
            reverse=True,
        )

        expiration_reports.append(
            {
                "expiration": expiration,
                "call_open_interest": call_open_interest,
                "put_open_interest": put_open_interest,
                "put_call_oi_ratio": _put_call_ratio(
                    put_open_interest,
                    call_open_interest,
                ),
                "call_volume": call_volume,
                "put_volume": put_volume,
                "put_call_volume_ratio": _put_call_ratio(
                    put_volume,
                    call_volume,
                ),
                "largest_call_oi": _highest_open_interest(calls),
                "largest_put_oi": _highest_open_interest(puts),
                "unusual_candidates": unusual_candidates[:3],
            }
        )

    return {
        "ticker": normalized,
        "current_price": current_price,
        "expiration_count": len(expirations),
        "analyzed_expirations": len(expiration_reports),
        "expirations": expiration_reports,
        "source": "Yahoo Finance via yfinance",
        "collected_at": collected_at,
        "data_status": "Latest available provider snapshot; may be delayed",
    }
def _format_ratio(value: float | None) -> str:
    """Format an optional ratio for Markdown output."""
    return "N/A" if value is None else f"{value:.2f}"


def _format_iv(value: float | None) -> str:
    """Format implied volatility without converting missing data to zero."""
    return "N/A" if value is None else f"{value * 100:.1f}%"

def _format_contract(contract: dict[str, Any] | None) -> str:
    """Format one maximum-OI contract for a compact table cell."""
    if not contract:
        return "N/A"

    implied_volatility = _format_iv(contract["implied_volatility"])

    return (
        f"${contract['strike']:.2f} "
        f"(OI {contract['open_interest']:,.0f}, "
        f"Vol {contract['volume']:,.0f}, "
        f"IV {implied_volatility})"
    )


def build_options_report(
    ticker: str,
    expiration_limit: int = 3,
) -> str:
    """Build a Markdown options-footprint report.

    Input: ticker and nearest-expiration limit.
    Output: Markdown report.
    Role: save option positioning clues for later probability scoring.
    """
    snapshot = collect_options_snapshot(ticker, expiration_limit)
    expirations = snapshot["expirations"]

    total_call_oi = sum(
        expiration["call_open_interest"]
        for expiration in expirations
    )
    total_put_oi = sum(
        expiration["put_open_interest"]
        for expiration in expirations
    )
    total_call_volume = sum(
        expiration["call_volume"]
        for expiration in expirations
    )
    total_put_volume = sum(
        expiration["put_volume"]
        for expiration in expirations
    )

    total_oi_ratio = _put_call_ratio(total_put_oi, total_call_oi)
    total_volume_ratio = _put_call_ratio(
        total_put_volume,
        total_call_volume,
    )

    lines = [
        "# Options Footprint Report",
        "",
        f"- **Ticker**: {snapshot['ticker']}",
        f"- **Reference price**: ${snapshot['current_price']:.2f}",
        (
            f"- **Analyzed expirations**: "
            f"{snapshot['analyzed_expirations']} "
            f"of {snapshot['expiration_count']}"
        ),
            f"- **Source**: {snapshot['source']}",
            f"- **Collected at (UTC)**: {snapshot.get('collected_at', 'N/A')}",
        (
            f"- **Data status**: "
            f"{snapshot.get('data_status', 'N/A')}"
        ),
        "",
        "",
        "## Combined summary",
        "",
        f"- **Call open interest**: {total_call_oi:,.0f}",
        f"- **Put open interest**: {total_put_oi:,.0f}",
        f"- **Put/Call OI ratio**: {_format_ratio(total_oi_ratio)}",
        f"- **Call volume**: {total_call_volume:,.0f}",
        f"- **Put volume**: {total_put_volume:,.0f}",
        (
            f"- **Put/Call volume ratio**: "
            f"{_format_ratio(total_volume_ratio)}"
        ),
        "",
        "## Expiration comparison",
        "",
        (
            "| Expiration | Call OI | Put OI | P/C OI | "
            "Call volume | Put volume | P/C volume |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for expiration in expirations:
        lines.append(
            f"| {expiration['expiration']} "
            f"| {expiration['call_open_interest']:,.0f} "
            f"| {expiration['put_open_interest']:,.0f} "
            f"| {_format_ratio(expiration['put_call_oi_ratio'])} "
            f"| {expiration['call_volume']:,.0f} "
            f"| {expiration['put_volume']:,.0f} "
            f"| {_format_ratio(expiration['put_call_volume_ratio'])} |"
        )

    lines.extend(
        [
            "",
            "## Largest open-interest strikes",
            "",
            "| Expiration | Largest Call OI | Largest Put OI |",
            "|---|---|---|",
        ]
    )

    for expiration in expirations:
        lines.append(
            f"| {expiration['expiration']} "
            f"| {_format_contract(expiration['largest_call_oi'])} "
            f"| {_format_contract(expiration['largest_put_oi'])} |"
        )

    lines.extend(
        [
            "",
            "## Unusual activity candidates",
            "",
            (
                "High volume/OI can flag new activity, but it does not "
                "identify the trader or prove bullish/bearish intent."
            ),
            "",
            (
                "| Expiration | Type | Strike | Volume | OI | "
                "Volume/OI | IV |"
            ),
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )

    candidate_count = 0
    for expiration in expirations:
        for candidate in expiration["unusual_candidates"]:
            candidate_count += 1
            lines.append(
                f"| {expiration['expiration']} "
                f"| {candidate['type']} "
                f"| ${candidate['strike']:.2f} "
                f"| {candidate['volume']:,.0f} "
                f"| {candidate['open_interest']:,.0f} "
                f"| {candidate['volume_oi_ratio']:.2f} "
                f"| {_format_iv(candidate['implied_volatility'])} |"
            )

    if candidate_count == 0:
        lines.append("| N/A | N/A | N/A | 0 | 0 | N/A | N/A |")

    if total_oi_ratio is None:
        positioning_text = "Put/Call OI could not be calculated."
    elif total_oi_ratio >= 1.0:
        positioning_text = (
            "Reported OI is put-heavy, which may reflect downside "
            "positioning or hedging demand."
        )
    elif total_oi_ratio <= 0.70:
        positioning_text = (
            "Reported OI is call-heavy, which may reflect upside "
            "positioning or covered-call supply."
        )
    else:
        positioning_text = (
            "Reported Put/Call OI is between the call-heavy and "
            "put-heavy reference zones."
        )

    lines.extend(
        [
            "",
            "## Preliminary interpretation",
            "",
            f"- {positioning_text}",
            (
                "- These values are clues, not proof of institutional "
                "buying, selling, or directional intent."
            ),
            (
                "- Open-interest change is not available from a single "
                "snapshot; repeated local snapshots are required."
            ),
            (
                "- Free provider data may be delayed, incomplete, or "
                "temporarily unavailable."
            ),
            "",
            "## TODO",
            "",
            "- Store dated snapshots and calculate OI change.",
            "- Add IV Rank and IV Percentile from historical snapshots.",
            "- Add gamma exposure when a verified data source is available.",
            "- Combine options clues with OBV, breadth, and sector flows.",
        ]
    )

    return "\n".join(lines) + "\n"