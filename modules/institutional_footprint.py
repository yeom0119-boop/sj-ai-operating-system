"""Estimate institutional money-in and money-out pressure.

This module combines technical indicators and option-chain summaries.
The scores are probability signals, not proof of institutional trading.
"""

from typing import Any

from modules.market_data import calculate_indicators, fetch_stock_history
from modules.options_data import collect_options_snapshot

def _safe_float(value: Any) -> float | None:
    """Convert a value to float when possible.

    Input: numeric-like value.
    Output: float or None.
    Role: prevent missing market data from breaking score calculation.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number != number:
        return None

    return number


def _average_expiration_ratio(
    options_snapshot: dict[str, Any],
    key: str,
) -> float | None:
    """Average a ratio across analyzed option expirations.

    Input: option snapshot and ratio field name.
    Output: average ratio or None.
    Role: reduce dependence on only one expiration date.
    """
    values = []

    for expiration in options_snapshot.get("expirations", []):
        value = _safe_float(expiration.get(key))
        if value is not None:
            values.append(value)

    if not values:
        return None

    return sum(values) / len(values)


def _add_signal(
    signals: list[dict[str, Any]],
    direction: str,
    weight: int,
    reason: str,
) -> None:
    """Append one explainable scoring signal.

    Input: signal list, direction, weight, and reason.
    Output: None.
    Role: keep every score contribution visible to the user.
    """
    signals.append(
        {
            "direction": direction,
            "weight": weight,
            "reason": reason,
        }
    )


def calculate_footprint_scores(
    indicator_data: Any,
    options_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Calculate preliminary Money In and Money Out scores.

    Input:
        indicator_data: DataFrame produced by calculate_indicators().
        options_snapshot: Dictionary produced by collect_options_snapshot().
    Output:
        Score dictionary containing inputs, scores, confidence, and reasons.
    Role:
        Combine graded technical and option signals into an explainable radar.

    The two scores are independent. Mixed evidence can raise both scores.
    """
    required_columns = [
        "Close",
        "Volume",
        "MA20",
        "MA60",
        "VOLUME20",
        "OBV",
        "RSI14",
    ]
    usable = indicator_data.dropna(subset=required_columns)

    if usable.empty:
        raise ValueError("not enough indicator data to calculate footprint scores")

    latest = usable.iloc[-1]
    earlier = usable.iloc[-6] if len(usable) >= 6 else usable.iloc[0]

    close = _safe_float(latest["Close"])
    volume = _safe_float(latest["Volume"])
    ma20 = _safe_float(latest["MA20"])
    ma60 = _safe_float(latest["MA60"])
    volume20 = _safe_float(latest["VOLUME20"])
    obv = _safe_float(latest["OBV"])
    earlier_obv = _safe_float(earlier["OBV"])
    rsi14 = _safe_float(latest["RSI14"])

    if None in (close, volume, ma20, ma60, volume20, obv, earlier_obv, rsi14):
        raise ValueError("required indicator values are missing")

    volume_ratio = volume / volume20 if volume20 > 0 else None
    obv_change = obv - earlier_obv

    put_call_oi = _average_expiration_ratio(
        options_snapshot,
        "put_call_oi_ratio",
    )
    put_call_volume = _average_expiration_ratio(
        options_snapshot,
        "put_call_volume_ratio",
    )

    money_in_score = 0
    money_out_score = 0
    available_weight = 0
    signals: list[dict[str, Any]] = []

    available_weight += 15
    if close >= ma20:
        money_in_score += 15
        _add_signal(signals, "IN", 15, "Price is at or above MA20")
    else:
        money_out_score += 15
        _add_signal(signals, "OUT", 15, "Price is below MA20")

    available_weight += 15
    if ma20 >= ma60:
        money_in_score += 15
        _add_signal(signals, "IN", 15, "MA20 is at or above MA60")
    else:
        money_out_score += 15
        _add_signal(signals, "OUT", 15, "MA20 is below MA60")

    available_weight += 20
    if obv_change > 0:
        money_in_score += 20
        _add_signal(signals, "IN", 20, "OBV increased over the comparison period")
    elif obv_change < 0:
        money_out_score += 20
        _add_signal(signals, "OUT", 20, "OBV decreased over the comparison period")
    else:
        _add_signal(signals, "NEUTRAL", 0, "OBV was unchanged")

    available_weight += 15
    if volume_ratio is not None and volume_ratio >= 1.2:
        if close >= ma20:
            money_in_score += 15
            _add_signal(
                signals,
                "IN",
                15,
                "High volume occurred while price was above MA20",
            )
        else:
            money_out_score += 15
            _add_signal(
                signals,
                "OUT",
                15,
                "High volume occurred while price was below MA20",
            )
    else:
        _add_signal(signals, "NEUTRAL", 0, "Volume was not strongly expanded")

    available_weight += 15
    if 55 <= rsi14 <= 70:
        money_in_score += 15
        _add_signal(signals, "IN", 15, "RSI14 is in the positive momentum zone")
    elif rsi14 < 45:
        money_out_score += 15
        _add_signal(signals, "OUT", 15, "RSI14 shows weak momentum")
    elif rsi14 > 75:
        money_out_score += 10
        _add_signal(
            signals,
            "OUT",
            10,
            "RSI14 is extended and raises profit-taking risk",
        )
    else:
        _add_signal(signals, "NEUTRAL", 0, "RSI14 is in a neutral zone")

    if put_call_oi is not None:
        available_weight += 10
        if put_call_oi < 0.7:
            money_in_score += 10
            _add_signal(signals, "IN", 10, "Put/Call open-interest ratio is below 0.70")
        elif put_call_oi > 1.0:
            money_out_score += 10
            _add_signal(signals, "OUT", 10, "Put/Call open-interest ratio is above 1.00")
        else:
            _add_signal(signals, "NEUTRAL", 0, "Put/Call OI ratio is balanced")

    if put_call_volume is not None:
        available_weight += 10
        if put_call_volume < 0.7:
            money_in_score += 10
            _add_signal(signals, "IN", 10, "Put/Call volume ratio is below 0.70")
        elif put_call_volume > 1.0:
            money_out_score += 10
            _add_signal(signals, "OUT", 10, "Put/Call volume ratio is above 1.00")
        else:
            _add_signal(signals, "NEUTRAL", 0, "Put/Call volume ratio is balanced")

    confidence = round(available_weight)

    return {
        "ticker": options_snapshot.get("ticker", ""),
        "money_in_score": min(100, round(money_in_score)),
        "money_out_score": min(100, round(money_out_score)),
        "data_coverage": min(100, confidence),
        "market_inputs": {
            "close": round(close, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "volume_ratio": (
                round(volume_ratio, 2) if volume_ratio is not None else None
            ),
            "obv_change": round(obv_change, 2),
            "rsi14": round(rsi14, 2),
            "put_call_oi_ratio": (
                round(put_call_oi, 2) if put_call_oi is not None else None
            ),
            "put_call_volume_ratio": (
                round(put_call_volume, 2)
                if put_call_volume is not None
                else None
            ),
        },
        "signals": signals,
        "warning": (
            "Probability-based research signal only. "
            "Option open interest does not reveal whether contracts were bought or sold."
        ),
    }

def build_footprint_report(
    ticker: str,
    expiration_limit: int = 3,
) -> str:
    """Build a Markdown institutional-footprint report.

    Input: ticker and number of option expirations to analyze.
    Output: Markdown report text.
    Role: download live inputs and present explainable Money In/Out scores.
    """
    history = fetch_stock_history(ticker, period="1y")
    indicators = calculate_indicators(history)
    options_snapshot = collect_options_snapshot(
        ticker,
        expiration_limit=expiration_limit,
    )
    result = calculate_footprint_scores(indicators, options_snapshot)
    inputs = result["market_inputs"]

    signal_lines = []
    for signal in result["signals"]:
        signal_lines.append(
            f'- **{signal["direction"]}** '
            f'(+{signal["weight"]}): {signal["reason"]}'
        )

    signals_text = "\n".join(signal_lines)

    return f"""# Institution Footprint Radar

- **Ticker**: {result["ticker"]}
- **Money In Score**: {result["money_in_score"]}/100
- **Money Out Score**: {result["money_out_score"]}/100
- **Data coverage**: {result["data_coverage"]}%
- **Source**: Yahoo Finance via yfinance

## Market inputs

| Indicator | Value |
|---|---:|
| Close | {inputs["close"]} |
| MA20 | {inputs["ma20"]} |
| MA60 | {inputs["ma60"]} |
| Volume / 20-day average | {inputs["volume_ratio"]} |
| OBV change | {inputs["obv_change"]} |
| RSI14 | {inputs["rsi14"]} |
| Put/Call OI ratio | {inputs["put_call_oi_ratio"]} |
| Put/Call volume ratio | {inputs["put_call_volume_ratio"]} |

## Score evidence

{signals_text}

## Interpretation warning

{result["warning"]}

This preliminary radar does not confirm institutional buying or selling.
Use official company guidance as the primary valuation source.
"""
# TODO: Add OI change, IV Rank, breadth, sector flow, VWAP, A/D, and short data.