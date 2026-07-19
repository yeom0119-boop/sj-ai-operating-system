"""Calculate preliminary institutional-footprint probability scores."""

from __future__ import annotations

import pandas as pd


def calculate_footprint_scores(data: pd.DataFrame) -> dict[str, object]:
    """Calculate weighted Money In and Money Out scores.

    Input:
        data: Indicator DataFrame created by calculate_indicators().
    Output:
        A dictionary containing 0–100 scores and supporting signal lists.
    Role:
        Combine graded technical signals without claiming confirmed institution trades.
    """
    required_columns = {
        "Close",
        "Volume",
        "MA20",
        "MA60",
        "MA150",
        "MA200",
        "VOLUME20",
        "OBV",
        "RSI14",
    }
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing indicator columns: {missing_text}")

    if len(data) < 21:
        raise ValueError("At least 21 trading days are required.")

    latest = data.iloc[-1]
    previous = data.iloc[-2]
    twenty_days_ago = data.iloc[-21]

    close_price = float(latest["Close"])
    daily_change = ((close_price / float(previous["Close"])) - 1) * 100
    volume_ratio = (float(latest["Volume"]) / float(latest["VOLUME20"])) * 100
    rsi14 = float(latest["RSI14"])

    money_in_score = 0
    money_out_score = 0
    money_in_signals: list[str] = []
    money_out_signals: list[str] = []

    moving_average_weights = {
        "MA20": 15,
        "MA60": 10,
        "MA150": 10,
        "MA200": 10,
    }

    for column, weight in moving_average_weights.items():
        average = latest[column]
        if pd.isna(average):
            continue
        if close_price >= float(average):
            money_in_score += weight
            money_in_signals.append(f"Price above {column} (+{weight})")
        else:
            money_out_score += weight
            money_out_signals.append(f"Price below {column} (+{weight})")

    if 55 <= rsi14 < 70:
        money_in_score += 15
        money_in_signals.append("RSI14 positive momentum (+15)")
    elif 50 <= rsi14 < 55:
        money_in_score += 8
        money_in_signals.append("RSI14 neutral-to-positive (+8)")
    elif rsi14 < 45:
        money_out_score += 15
        money_out_signals.append("RSI14 weak momentum (+15)")
    elif rsi14 < 50:
        money_out_score += 8
        money_out_signals.append("RSI14 neutral-to-weak (+8)")

    if float(latest["OBV"]) > float(twenty_days_ago["OBV"]):
        money_in_score += 20
        money_in_signals.append("OBV higher than 20 trading days ago (+20)")
    elif float(latest["OBV"]) < float(twenty_days_ago["OBV"]):
        money_out_score += 20
        money_out_signals.append("OBV lower than 20 trading days ago (+20)")

    if daily_change > 0 and volume_ratio >= 120:
        money_in_score += 20
        money_in_signals.append("Price up with volume at least 120% of average (+20)")
    elif daily_change > 0 and volume_ratio >= 100:
        money_in_score += 10
        money_in_signals.append("Price up with above-average volume (+10)")
    elif daily_change < 0 and volume_ratio >= 120:
        money_out_score += 20
        money_out_signals.append("Price down with volume at least 120% of average (+20)")
    elif daily_change < 0 and volume_ratio >= 100:
        money_out_score += 10
        money_out_signals.append("Price down with above-average volume (+10)")

    return {
        "money_in_score": min(money_in_score, 100),
        "money_out_score": min(money_out_score, 100),
        "money_in_signals": money_in_signals,
        "money_out_signals": money_out_signals,
        "daily_change_pct": daily_change,
        "volume_ratio_pct": volume_ratio,
    }