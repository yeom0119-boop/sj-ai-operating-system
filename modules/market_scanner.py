"""Prepare the U.S. stock universe for the Market Scanner."""

import csv
import json
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from modules.market_data import calculate_indicators
from modules.watchlist import normalize_ticker


NASDAQ_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
)
OTHER_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
)
DIRECTORY_TIMEOUT_SECONDS = 30
MARKET_DATA_BATCH_SIZE = 100
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKET_SCANNER_CONFIG_PATH = PROJECT_ROOT / "config" / "market_scanner.json"
MARKET_DATA_PERIOD = "1mo"
TECHNICAL_DATA_PERIOD = "2y"
TECHNICAL_DATA_INTERVAL = "1d"
EXCLUDED_SECURITY_PATTERN = re.compile(
    r"\b("
    r"warrants?|"
    r"rights?|"
    r"units?|"
    r"preferred stock|"
    r"preferred shares?|"
    r"senior notes?|"
    r"notes due|"
    r"debentures?"
    r")\b",
    re.IGNORECASE,
)
def load_market_scanner_config(
    config_path: Path = MARKET_SCANNER_CONFIG_PATH,
) -> dict[str, object]:
    """Load and validate the Market Scanner configuration.

    Input: path to a Market Scanner JSON configuration file.
    Output: dictionary containing every required scanner setting.
    Role: keep scanner thresholds outside the Python source code.
    """
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"market scanner config not found: {config_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid market scanner JSON: {config_path}"
        ) from error

    if not isinstance(config, dict):
        raise ValueError("market scanner config must be a JSON object")

    required_keys = {
        "min_price",
        "min_average_volume",
        "min_average_dollar_volume",
        "min_rsi",
        "max_rsi",
        "max_price_vs_ma20_pct",
        "require_above_ma20",
        "require_rising_ma200",
        "require_rising_obv",
        "require_stage_two",
        "require_rising_ad",
        "batch_size",
        "max_candidates",
        "deep_analysis_limit",
    }
    missing_keys = sorted(required_keys - config.keys())

    if missing_keys:
        raise ValueError(
            "market scanner config is missing: "
            + ", ".join(missing_keys)
        )

    return config

def is_supported_stock(security_name: str) -> bool:
    """Return whether a security description represents a supported stock.

    Input: official security name from an exchange directory.
    Output: True for supported stocks and False for excluded security types.
    Role: remove warrants, rights, units, preferred shares, and debt securities.
    """
    return EXCLUDED_SECURITY_PATTERN.search(security_name) is None

def prepare_market_universe(symbols: list[str]) -> list[str]:
    """Return unique, validated ticker symbols for market scanning.

    Input: raw ticker symbols collected from a market-listing source.
    Output: sorted list of unique and valid ticker symbols.
    Role: clean the full-market symbol list before data collection and filtering.
    """
    valid_symbols = []

    for symbol in symbols:
        if not isinstance(symbol, str):
            continue

        try:
            valid_symbols.append(normalize_ticker(symbol))
        except ValueError:
            # Skip malformed symbols without stopping the full-market scan.
            continue

    return sorted(set(valid_symbols))


def parse_symbol_directory(
    directory_text: str,
    symbol_column: str,
) -> list[str]:
    """Extract tradable stock symbols from a Nasdaq directory file.

    Input: pipe-delimited directory text and the name of its symbol column.
    Output: sorted list of valid non-test, non-ETF ticker symbols.
    Role: convert official exchange directory data into scanner-ready symbols.
    """
    reader = csv.DictReader(StringIO(directory_text), delimiter="|")

    if not reader.fieldnames or symbol_column not in reader.fieldnames:
        raise ValueError(f"symbol directory is missing column: {symbol_column}")

    symbols = []

    for row in reader:
        symbol = (row.get(symbol_column) or "").strip()

        if not symbol or symbol == "File Creation Time":
            continue

        if (row.get("Test Issue") or "").strip().upper() == "Y":
            continue

        if (row.get("ETF") or "").strip().upper() == "Y":
            continue

        security_name = (row.get("Security Name") or "").strip()
        if not is_supported_stock(security_name):
            continue

        symbols.append(symbol)        

    return prepare_market_universe(symbols)


def download_symbol_directory(url: str) -> str:
    """Download one official market symbol directory.

    Input: official Nasdaq Trader directory URL.
    Output: downloaded pipe-delimited text.
    Role: retrieve the latest exchange-listed symbols with a fixed timeout.
    """
    response = requests.get(
        url,
        timeout=DIRECTORY_TIMEOUT_SECONDS,
        headers={"User-Agent": "SJ AI Operating System/2.0"},
    )
    response.raise_for_status()
    return response.text


def collect_us_market_universe() -> list[str]:
    """Collect the current U.S. market stock universe.

    Input: latest Nasdaq and other-exchange directory files.
    Output: combined, unique, sorted list of non-ETF ticker symbols.
    Role: provide full-market candidates for the scanner filtering stage.
    """
    nasdaq_text = download_symbol_directory(NASDAQ_LISTED_URL)
    other_text = download_symbol_directory(OTHER_LISTED_URL)

    nasdaq_symbols = parse_symbol_directory(nasdaq_text, "Symbol")
    other_symbols = parse_symbol_directory(other_text, "ACT Symbol")

    return prepare_market_universe(nasdaq_symbols + other_symbols)

def collect_market_rows(
    tickers: list[str],
    batch_size: int = MARKET_DATA_BATCH_SIZE,
) -> list[dict[str, object]]:
    """Collect latest price and average volume in manageable batches.

    Input: market ticker symbols and the number downloaded per request.
    Output: normalized rows containing ticker, price, and average volume.
    Role: prepare full-market liquidity data before candidate filtering.
    """
    if batch_size <= 0:
        raise ValueError("market data batch size must be positive")

    normalized_tickers = prepare_market_universe(tickers)
    market_rows = []

    for start in range(0, len(normalized_tickers), batch_size):
        ticker_batch = normalized_tickers[start : start + batch_size]
        provider_tickers = [
            ticker.replace(".", "-")
            for ticker in ticker_batch
        ]

        try:
            history = yf.download(
                provider_tickers,
                period=MARKET_DATA_PERIOD,
                interval="1d",
                group_by="column",
                auto_adjust=False,
                progress=False,
                threads=True,
                timeout=DIRECTORY_TIMEOUT_SECONDS,
            )
        except Exception:
            # Skip one failed provider batch and continue the full scan.
            continue

        if history.empty:
            continue

        has_multiple_column_levels = (
            getattr(history.columns, "nlevels", 1) > 1
        )

        for ticker, provider_ticker in zip(
            ticker_batch,
            provider_tickers,
        ):
            try:
                if has_multiple_column_levels:
                    close_values = history[("Close", provider_ticker)]
                    volume_values = history[("Volume", provider_ticker)]
                else:
                    close_values = history["Close"]
                    volume_values = history["Volume"]

                valid_close_values = close_values.dropna()
                valid_volume_values = volume_values.dropna()

                if valid_close_values.empty or valid_volume_values.empty:
                    continue

                price = float(valid_close_values.iloc[-1])
                average_volume = float(valid_volume_values.mean())
            except (KeyError, TypeError, ValueError):
                # One unavailable ticker must not stop the full-market scan.
                continue

            market_rows.append(
                {
                    "ticker": ticker,
                    "price": round(price, 2),
                    "average_volume": round(average_volume),
                }
            )

    return sorted(market_rows, key=lambda row: row["ticker"])
def calculate_vcp_tcv_score(
    is_stage_two: bool,
    price_range_60_pct: float,
    price_range_20_pct: float,
    price_range_10_pct: float,
    average_volume_50: float,
    average_volume_20: float,
    average_volume_10: float,
) -> int:
    """Calculate the SJ VCP/TCV setup score.

    Input:
        Stage 2 status, price-range percentages, and average volumes.
    Output:
        Integer score between 0 and 100.
    Role:
        Measure trend, volatility contraction, volume contraction,
        and final price tightness using transparent rules.
    """
    score = 0

    if is_stage_two:
        score += 10

    if price_range_20_pct < price_range_60_pct:
        score += 20

    if price_range_10_pct < price_range_20_pct:
        score += 20

    if average_volume_20 < average_volume_50:
        score += 15

    if average_volume_10 < average_volume_20:
        score += 15

    if price_range_10_pct <= 8.0:
        score += 10

    if price_range_20_pct <= 15.0:
        score += 10

    return score


def build_technical_snapshot(
    ticker: str,
    data: pd.DataFrame,
) -> dict[str, object] | None:
    """Build the latest technical-indicator snapshot for one stock.

    Input:
        ticker: Stock ticker being analyzed.
        data: Historical OHLCV data with enough rows for MA200.
    Output:
        Latest technical values, or None when required data is unavailable.
    Role:
        Convert historical data into second-stage scanner inputs.
    """
    required_columns = {"Close", "High", "Low", "Volume"}

    if data.empty or not required_columns.issubset(data.columns):
        return None

    indicators = calculate_indicators(data)
    indicator_columns = [
                "Close",
        "MA20",
        "MA50",
        "MA60",
        "MA150",
        "MA200",
        "VOLUME20",
        "OBV",
        "AD",
        "RSI14",
    ]
    latest = indicators.iloc[-1]

    if latest[indicator_columns].isna().any():
        return None

    twenty_sessions_ago = indicators.iloc[-21]
    ma150_20_sessions_ago = twenty_sessions_ago["MA150"]
    ma200_20_sessions_ago = twenty_sessions_ago["MA200"]
    obv_change_20 = latest["OBV"] - twenty_sessions_ago["OBV"]
    ad_change_20 = latest["AD"] - twenty_sessions_ago["AD"]

    price = float(latest["Close"])
    ma20 = float(latest["MA20"])
    average_volume_20 = float(latest["VOLUME20"])
    normalization_volume_20 = average_volume_20 * 20
    recent_60 = indicators[
        ["High", "Low", "Volume"]
    ].tail(60).dropna()

    if len(recent_60) < 60:
        return None

    recent_20 = recent_60.tail(20)
    recent_10 = recent_60.tail(10)

    low_60 = float(recent_60["Low"].min())
    low_20 = float(recent_20["Low"].min())
    low_10 = float(recent_10["Low"].min())

    if low_60 <= 0 or low_20 <= 0 or low_10 <= 0:
        return None

    price_range_60_pct = (
        (float(recent_60["High"].max()) / low_60) - 1
    ) * 100
    price_range_20_pct = (
        (float(recent_20["High"].max()) / low_20) - 1
    ) * 100
    price_range_10_pct = (
        (float(recent_10["High"].max()) / low_10) - 1
    ) * 100

    average_volume_50 = float(
        recent_60["Volume"].tail(50).mean()
    )
    average_volume_10 = float(recent_10["Volume"].mean())

    ma50 = float(latest["MA50"])
    ma150 = float(latest["MA150"])
    ma200 = float(latest["MA200"])

    is_stage_two = (
        price > ma150
        and ma50 > ma150 > ma200
        and ma150 > float(ma150_20_sessions_ago)
        and ma200 > float(ma200_20_sessions_ago)
    )
    vcp_tcv_score = calculate_vcp_tcv_score(
        is_stage_two=is_stage_two,
        price_range_60_pct=price_range_60_pct,
        price_range_20_pct=price_range_20_pct,
        price_range_10_pct=price_range_10_pct,
        average_volume_50=average_volume_50,
        average_volume_20=average_volume_20,
        average_volume_10=average_volume_10,
    )

    if ma20 <= 0 or normalization_volume_20 <= 0:
        return None

    price_vs_ma20_pct = ((price / ma20) - 1) * 100
    obv_change_ratio_20 = obv_change_20 / normalization_volume_20
    ad_change_ratio_20 = ad_change_20 / normalization_volume_20

    return {
        "ticker": normalize_ticker(ticker),
        "price": round(price, 2),
        "ma20": round(ma20, 2),
        "price_vs_ma20_pct": round(price_vs_ma20_pct, 2),
        "ma50": round(float(latest["MA50"]), 2),
        "ma60": round(float(latest["MA60"]), 2),
        "ma150": round(float(latest["MA150"]), 2),
        "ma150_20_sessions_ago": round(
            float(ma150_20_sessions_ago),
            2,
        ),
        "ma200": round(float(latest["MA200"]), 2),
        "ma200_20_sessions_ago": round(float(ma200_20_sessions_ago), 2),
        "average_volume_20": round(float(latest["VOLUME20"])),
        "obv": round(float(latest["OBV"]), 2),
        "obv_change_20": round(float(obv_change_20), 2),
        "obv_change_ratio_20": round(float(obv_change_ratio_20), 4),
        "ad": round(float(latest["AD"]), 2),
        "ad_change_20": round(float(ad_change_20), 2),
        "ad_change_ratio_20": round(float(ad_change_ratio_20), 4),
        "rsi14": round(float(latest["RSI14"]), 2),
        "is_stage_two": is_stage_two,
        "vcp_tcv_score": vcp_tcv_score,
    }

def collect_technical_rows(
    candidates: list[dict[str, object]],
    batch_size: int = MARKET_DATA_BATCH_SIZE,
) -> list[dict[str, object]]:
    """Collect technical snapshots only for liquid market candidates.

    Input:
        candidates: Stocks that passed the first-stage liquidity filter.
        batch_size: Number of tickers downloaded in each provider request.
    Output:
        Latest valid technical-indicator snapshots sorted by ticker.
    Role:
        Limit expensive two-year data collection to liquid candidates.
    """
    if batch_size <= 0:
        raise ValueError("technical data batch size must be positive")

    candidate_tickers = prepare_market_universe(
        [
            str(candidate["ticker"])
            for candidate in candidates
            if isinstance(candidate, dict) and "ticker" in candidate
        ]
    )
    technical_rows = []

    for start in range(0, len(candidate_tickers), batch_size):
        ticker_batch = candidate_tickers[start : start + batch_size]
        provider_tickers = [
            ticker.replace(".", "-")
            for ticker in ticker_batch
        ]

        try:
            history = yf.download(
                provider_tickers,
                period=TECHNICAL_DATA_PERIOD,
                interval=TECHNICAL_DATA_INTERVAL,
                group_by="column",
                auto_adjust=False,
                progress=False,
                threads=True,
                timeout=DIRECTORY_TIMEOUT_SECONDS,
            )
        except Exception:
            # Skip one failed provider batch and continue the full scan.
            continue

        if history.empty:
            continue

        has_multiple_column_levels = (
            getattr(history.columns, "nlevels", 1) > 1
        )

        for ticker, provider_ticker in zip(
            ticker_batch,
            provider_tickers,
        ):
            try:
                if has_multiple_column_levels:
                    ticker_history = pd.DataFrame(
                        {
                            "Close": history[("Close", provider_ticker)],
                            "High": history[("High", provider_ticker)],
                            "Low": history[("Low", provider_ticker)],
                            "Volume": history[("Volume", provider_ticker)],
                        }
                    )
                else:
                    ticker_history = history[
                        ["Close", "High", "Low", "Volume"]
                    ].copy()

                snapshot = build_technical_snapshot(
                    ticker,
                    ticker_history,
                )
            except (KeyError, TypeError, ValueError):
                # One incomplete ticker must not stop other candidates.
                continue

            if snapshot is not None:
                technical_rows.append(snapshot)

    return sorted(
        technical_rows,
        key=lambda row: row["ticker"],
    )

def filter_technical_candidates(
    technical_rows: list[dict[str, object]],
    min_rsi: float,
    max_rsi: float,
    max_price_vs_ma20_pct: float,
    require_above_ma20: bool,
    require_rising_obv: bool,
    require_rising_ad: bool,
    require_ma_alignment: bool = False,
    require_rising_ma200: bool = False,
    require_stage_two: bool = False,
) -> list[dict[str, object]]:
    """Filter liquid candidates using configurable technical rules.

    Input:
        technical_rows: Latest indicator snapshots for liquid stocks.
        min_rsi: Minimum acceptable RSI14 value.
        max_rsi: Maximum acceptable RSI14 value.
        max_price_vs_ma20_pct: Maximum allowed price extension above MA20.
        require_above_ma20: Whether price must be above MA20.
        require_rising_obv: Whether 20-session OBV change must be positive.
        require_rising_ad: Whether 20-session A/D change must be positive.
        require_ma_alignment: Whether MA20 > MA50 > MA150 > MA200 is required.
        require_rising_ma200: Whether MA200 must be above its value 20 sessions ago.
        require_stage_two: Whether the stock must be in a confirmed Stage 2 uptrend.
    Output:
        Technical candidates that satisfy every enabled rule.
    Role:
        Apply the second-stage SJ technical screening principles.
    """
    if (
        min_rsi < 0
        or max_rsi > 100
        or min_rsi > max_rsi
    ):
        raise ValueError("RSI range must be between 0 and 100")
    if max_price_vs_ma20_pct < 0:
        raise ValueError("maximum MA20 extension cannot be negative")

    candidates = []

    for row in technical_rows:
        try:
            price = float(row["price"])
            ma20 = float(row["ma20"])
            rsi14 = float(row["rsi14"])
            obv_change_20 = float(row["obv_change_20"])
            ad_change_20 = float(row["ad_change_20"])
        except (KeyError, TypeError, ValueError):
            # Skip incomplete rows without stopping the market scan.
            continue

        if rsi14 < min_rsi or rsi14 > max_rsi:
            continue

        if ma20 <= 0:
            continue

        price_vs_ma20_pct = ((price / ma20) - 1) * 100
        if price_vs_ma20_pct > max_price_vs_ma20_pct:
            continue

        if require_above_ma20 and price <= ma20:
            continue

        if require_ma_alignment:
            try:
                ma50 = float(row["ma50"])
                ma150 = float(row["ma150"])
                ma200 = float(row["ma200"])
            except (KeyError, TypeError, ValueError):
                continue

            if not ma20 > ma50 > ma150 > ma200:
                continue

        if require_stage_two:
            try:
                ma50 = float(row["ma50"])
                ma150 = float(row["ma150"])
                ma150_20_sessions_ago = float(
                    row["ma150_20_sessions_ago"]
                )
                ma200 = float(row["ma200"])
                ma200_20_sessions_ago = float(
                    row["ma200_20_sessions_ago"]
                )
            except (KeyError, TypeError, ValueError):
                continue

            is_stage_two = (
                price > ma150
                and ma50 > ma150 > ma200
                and ma150 > ma150_20_sessions_ago
                and ma200 > ma200_20_sessions_ago
            )
            if not is_stage_two:
                continue
        if require_rising_ma200:
            try:
                ma200 = float(row["ma200"])
                ma200_20_sessions_ago = float(
                    row["ma200_20_sessions_ago"]
                )
            except (KeyError, TypeError, ValueError):
                continue

            if ma200 <= ma200_20_sessions_ago:
                continue

        if require_rising_obv and obv_change_20 <= 0:
            continue

        if require_rising_ad and ad_change_20 <= 0:
            continue

        candidates.append(row)

    return sorted(
        candidates,
        key=lambda candidate: str(candidate["ticker"]),
    )


def rank_technical_candidates(
    candidates: list[dict[str, object]],
    max_candidates: int,
) -> list[dict[str, object]]:
    """Rank and limit technically qualified market candidates.

    Input:
        Filtered technical rows and the maximum result count.
    Output:
        Ranked candidate copies with footprint strength and rank.
    Role:
        Prioritize comparable institutional-footprint signals before
        expensive deep analysis.
    """
    if max_candidates <= 0:
        raise ValueError("maximum scanner candidates must be positive")

    valid_candidates = []

    for candidate in candidates:
        try:
            ticker = normalize_ticker(str(candidate["ticker"]))
            obv_ratio = float(candidate["obv_change_ratio_20"])
            ad_ratio = float(candidate["ad_change_ratio_20"])
            rsi14 = float(candidate["rsi14"])
            price_extension = float(candidate["price_vs_ma20_pct"])
            vcp_tcv_score = float(
            candidate.get("vcp_tcv_score", 0)
            )
        except (KeyError, TypeError, ValueError):
            continue

        ranked_candidate = candidate.copy()
        ranked_candidate["ticker"] = ticker
        ranked_candidate["vcp_tcv_score"] = round(vcp_tcv_score)
        ranked_candidate["footprint_strength"] = round(
            obv_ratio + ad_ratio,
            4,
        )
        valid_candidates.append(ranked_candidate)

    valid_candidates.sort(
        key=lambda candidate: (
            -float(candidate["vcp_tcv_score"]),
            -float(candidate["footprint_strength"]),
            abs(float(candidate["rsi14"]) - 60.0),
            float(candidate["price_vs_ma20_pct"]),
            str(candidate["ticker"]),
        )
    )

    limited_candidates = valid_candidates[:max_candidates]

    for position, candidate in enumerate(limited_candidates, start=1):
        candidate["technical_rank"] = position

    return limited_candidates

def filter_market_candidates(
    market_rows: list[dict[str, object]],
    min_price: float,
    min_average_volume: int,
    min_average_dollar_volume: float,
) -> list[dict[str, object]]:
    """Filter the market universe by price and trading liquidity.

    Input: ticker market rows and configurable minimum thresholds.
    Output: sorted candidate rows that satisfy every threshold.
    Role: reduce the full market before expensive deep analysis.
    """
    if (
        min_price < 0
        or min_average_volume < 0
        or min_average_dollar_volume < 0
    ):
        raise ValueError("scanner thresholds cannot be negative")

    candidates = []

    for row in market_rows:
        try:
            ticker = normalize_ticker(str(row["ticker"]))
            price = float(row["price"])
            average_volume = float(row["average_volume"])
        except (KeyError, TypeError, ValueError):
            # Skip incomplete provider rows without stopping the full scan.
            continue

        if price < 0 or average_volume < 0:
            continue

        average_dollar_volume = price * average_volume

        if price < min_price:
            continue

        if average_volume < min_average_volume:
            continue

        if average_dollar_volume < min_average_dollar_volume:
            continue

        candidates.append(
            {
                "ticker": ticker,
                "price": round(price, 2),
                "average_volume": round(average_volume),
                "average_dollar_volume": round(
                    average_dollar_volume,
                    2,
                ),
            }
        )

    return sorted(candidates, key=lambda candidate: candidate["ticker"])


def scan_us_market(
    min_price: float,
    min_average_volume: int,
    min_average_dollar_volume: float,
    batch_size: int = MARKET_DATA_BATCH_SIZE,
) -> list[dict[str, object]]:
    """Run the first-stage full U.S. market liquidity scan.

    Input: configurable liquidity thresholds and provider batch size.
    Output: market candidates that pass every first-stage filter.
    Role: connect universe collection, market data, and filtering.
    """
    universe = collect_us_market_universe()
    market_rows = collect_market_rows(
        universe,
        batch_size=batch_size,
    )

    return filter_market_candidates(
        market_rows,
        min_price=min_price,
        min_average_volume=min_average_volume,
        min_average_dollar_volume=min_average_dollar_volume,
    )

def scan_us_market_technical_candidates(
    min_price: float,
    min_average_volume: int,
    min_average_dollar_volume: float,
    min_rsi: float,
    max_rsi: float,
    max_price_vs_ma20_pct: float,
    require_above_ma20: bool,
    require_rising_obv: bool,
    require_rising_ad: bool,
    require_ma_alignment: bool = False,
    require_rising_ma200: bool = False,
    require_stage_two: bool = False,
    batch_size: int = MARKET_DATA_BATCH_SIZE,
) -> list[dict[str, object]]:
    """Run the connected liquidity and technical market scan.

    Input:
        Liquidity thresholds, technical rules, and provider batch size.
    Output:
        Full-market candidates that pass both scanner stages.
    Role:
        Connect low-cost liquidity filtering to focused technical analysis.
    """
    liquidity_candidates = scan_us_market(
        min_price=min_price,
        min_average_volume=min_average_volume,
        min_average_dollar_volume=min_average_dollar_volume,
        batch_size=batch_size,
    )
    technical_rows = collect_technical_rows(
        liquidity_candidates,
        batch_size=batch_size,
    )

    return filter_technical_candidates(
        technical_rows,
        min_rsi=min_rsi,
        max_rsi=max_rsi,
        max_price_vs_ma20_pct=max_price_vs_ma20_pct,
        require_above_ma20=require_above_ma20,
        require_rising_obv=require_rising_obv,
        require_rising_ad=require_rising_ad,
        require_ma_alignment=require_ma_alignment,
        require_rising_ma200=require_rising_ma200,
        require_stage_two=require_stage_two,
    )