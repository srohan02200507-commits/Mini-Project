from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from app.models import MarketData, Stock


class MarketDataUnavailableError(Exception):
    """Raised when live or historical market data cannot be retrieved for a target time."""


SUPPORTED_REAL_TICKERS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla, Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil Corporation",
    "SPY": "SPDR S&P 500 ETF Trust",
}


def _yahoo_chart_request(symbol: str, range_str: str = "6mo", interval: str = "1d") -> dict:
    clean_symbol = urllib.parse.quote(symbol.strip().upper())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}?range={range_str}&interval={interval}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TradeWiseAI/2.1",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                raise MarketDataUnavailableError(f"Market provider returned HTTP {resp.status} for {symbol}.")
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise MarketDataUnavailableError(f"Real market provider unreachable for {symbol}: {exc}") from exc

    chart = payload.get("chart") or {}
    if chart.get("error"):
        desc = chart["error"].get("description") or "Unknown provider error"
        raise MarketDataUnavailableError(f"Market provider error for {symbol}: {desc}")

    results = chart.get("result") or []
    if not results:
        raise MarketDataUnavailableError(f"No real market data returned for {symbol}.")

    return results[0]


def fetch_real_market_series(symbol: str, range_str: str = "6mo", interval: str = "1d") -> tuple[dict, pd.DataFrame]:
    clean_symbol = symbol.strip().upper()
    result = _yahoo_chart_request(clean_symbol, range_str=range_str, interval=interval)
    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quote_list = (result.get("indicators") or {}).get("quote") or []
    if not timestamps or not quote_list:
        raise MarketDataUnavailableError(f"Incomplete market series returned for {clean_symbol}.")

    q = quote_list[0]
    opens = q.get("open") or []
    highs = q.get("high") or []
    lows = q.get("low") or []
    closes = q.get("close") or []
    volumes = q.get("volume") or []

    rows = []
    for idx, ts in enumerate(timestamps):
        c = closes[idx] if idx < len(closes) else None
        o = opens[idx] if idx < len(opens) else None
        h = highs[idx] if idx < len(highs) else None
        l = lows[idx] if idx < len(lows) else None
        v = volumes[idx] if idx < len(volumes) else None
        if c is None or o is None or h is None or l is None:
            continue
        dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
        rows.append(
            {
                "timestamp": dt_utc,
                "date": dt_utc.date(),
                "open": round(float(o), 2),
                "high": round(float(h), 2),
                "low": round(float(l), 2),
                "close": round(float(c), 2),
                "volume": int(v or 0),
            }
        )

    if not rows:
        raise MarketDataUnavailableError(f"No valid OHLCV bars found for {clean_symbol}.")

    df = pd.DataFrame(rows)
    latest_close = float(df.iloc[-1]["close"])
    prev_close = float(df.iloc[-2]["close"]) if len(df) >= 2 else float(meta.get("chartPreviousClose") or latest_close)
    current_price = float(meta.get("regularMarketPrice") or latest_close)
    day_change_pct = ((current_price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0

    stock_meta = {
        "symbol": clean_symbol,
        "name": meta.get("longName") or meta.get("shortName") or SUPPORTED_REAL_TICKERS.get(clean_symbol, clean_symbol),
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchangeName", "NASDAQ/NYSE"),
        "current_price": round(current_price, 2),
        "previous_close": round(prev_close, 2),
        "day_change_pct": round(day_change_pct, 2),
        "data_source": "REAL_MARKET",
        "is_simulated": False,
        "last_updated": df.iloc[-1]["timestamp"].isoformat(),
    }
    return stock_meta, df


def fetch_simulated_market_series(symbol: str) -> tuple[dict, pd.DataFrame]:
    clean_symbol = symbol.strip().upper()
    stock = Stock.query.filter_by(symbol=clean_symbol).first()
    if not stock:
        raise MarketDataUnavailableError(f"Simulated stock '{clean_symbol}' does not exist in local database.")

    bars = MarketData.query.filter_by(stock_id=stock.id).order_by(MarketData.date.asc()).all()
    if not bars:
        raise MarketDataUnavailableError(f"No simulated OHLCV history available for '{clean_symbol}'.")

    df = pd.DataFrame(
        [
            {
                "timestamp": datetime.combine(b.date, datetime.min.time()),
                "date": b.date,
                "open": float(b.open_price),
                "high": float(b.high_price),
                "low": float(b.low_price),
                "close": float(b.close_price),
                "volume": int(b.volume),
            }
            for b in bars
        ]
    )

    stock_meta = {
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "current_price": round(float(stock.current_price), 2),
        "previous_close": round(float(stock.previous_close), 2),
        "day_change_pct": round(float(stock.day_change_pct), 2),
        "data_source": "SIMULATED_TEST",
        "is_simulated": True,
        "last_updated": stock.last_updated_date.isoformat(),
    }
    return stock_meta, df


def get_market_series(symbol: str, data_source: str = "REAL_MARKET") -> tuple[dict, pd.DataFrame]:
    source = (data_source or "REAL_MARKET").strip().upper()
    if source == "SIMULATED_TEST":
        return fetch_simulated_market_series(symbol)
    return fetch_real_market_series(symbol)


def fetch_actual_price_for_target(
    symbol: str,
    target_timestamp: datetime,
    data_source: str = "REAL_MARKET",
) -> tuple[float, datetime]:
    """
    Strictly retrieves the actual market price at or after `target_timestamp`.
    Raises MarketDataUnavailableError if no verified market bar exists yet or if provider is offline.
    Never invents or fabricates actual prices.
    """
    source = (data_source or "REAL_MARKET").strip().upper()
    clean_symbol = symbol.strip().upper()

    if source == "SIMULATED_TEST":
        stock = Stock.query.filter_by(symbol=clean_symbol).first()
        if not stock:
            raise MarketDataUnavailableError(f"Simulated symbol '{clean_symbol}' not found.")

        bar = (
            MarketData.query.filter(
                MarketData.stock_id == stock.id,
                MarketData.date >= target_timestamp.date(),
            )
            .order_by(MarketData.date.asc())
            .first()
        )
        if not bar:
            raise MarketDataUnavailableError(
                f"No simulated bar available yet for {clean_symbol} on or after {target_timestamp.date().isoformat()}."
            )
        return round(float(bar.close_price), 2), datetime.combine(bar.date, datetime.min.time())

    # REAL_MARKET mode
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    age_days = (now_utc - target_timestamp).total_seconds() / 86400.0

    # Try hourly bars first if target is within the last 5 days so short horizons verify accurately
    if age_days <= 5.0:
        try:
            _, hourly_df = fetch_real_market_series(clean_symbol, range_str="5d", interval="60m")
            matching = hourly_df[hourly_df["timestamp"] >= target_timestamp]
            if not matching.empty:
                first_bar = matching.iloc[0]
                return round(float(first_bar["close"]), 2), first_bar["timestamp"].to_pydatetime()
        except MarketDataUnavailableError:
            pass

    _, daily_df = fetch_real_market_series(clean_symbol, range_str="6mo", interval="1d")
    matching_daily = daily_df[daily_df["date"] >= target_timestamp.date()]
    if matching_daily.empty:
        raise MarketDataUnavailableError(
            f"Real market data for {clean_symbol} on or after {target_timestamp.date().isoformat()} is not available yet."
        )
    first_daily = matching_daily.iloc[0]
    return round(float(first_daily["close"]), 2), first_daily["timestamp"].to_pydatetime()


def fetch_real_time_quote(symbol: str, include_intraday: bool = False) -> dict:
    """Fetches latest real-time quote (and optional 5-minute intraday series) from Yahoo Finance."""
    clean_symbol = symbol.strip().upper()
    range_str = "1d" if include_intraday else "5d"
    interval = "5m" if include_intraday else "1d"
    result = _yahoo_chart_request(clean_symbol, range_str=range_str, interval=interval)
    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quote_list = (result.get("indicators") or {}).get("quote") or []

    intraday_bars = []
    if timestamps and quote_list:
        q = quote_list[0]
        opens = q.get("open") or []
        highs = q.get("high") or []
        lows = q.get("low") or []
        closes = q.get("close") or []
        volumes = q.get("volume") or []
        for idx, ts in enumerate(timestamps):
            c = closes[idx] if idx < len(closes) else None
            if c is None:
                continue
            dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
            intraday_bars.append(
                {
                    "timestamp": dt_utc.isoformat(),
                    "time_label": dt_utc.strftime("%H:%M") if include_intraday else dt_utc.strftime("%m-%d"),
                    "open": round(float(opens[idx] if idx < len(opens) and opens[idx] is not None else c), 2),
                    "high": round(float(highs[idx] if idx < len(highs) and highs[idx] is not None else c), 2),
                    "low": round(float(lows[idx] if idx < len(lows) and lows[idx] is not None else c), 2),
                    "close": round(float(c), 2),
                    "volume": int(volumes[idx] if idx < len(volumes) and volumes[idx] is not None else 0),
                }
            )

    last_price = float(
        meta.get("regularMarketPrice")
        or (intraday_bars[-1]["close"] if intraday_bars else 0.0)
    )
    if last_price <= 0:
        raise MarketDataUnavailableError(f"Real-time quote unavailable for {clean_symbol}.")

    prev_close = float(meta.get("chartPreviousClose") or meta.get("previousClose") or last_price)
    day_change = last_price - prev_close
    day_change_pct = (day_change / prev_close) * 100.0 if prev_close > 0 else 0.0

    quote = {
        "symbol": clean_symbol,
        "name": meta.get("longName") or meta.get("shortName") or SUPPORTED_REAL_TICKERS.get(clean_symbol, clean_symbol),
        "exchange": meta.get("exchangeName", "US Market"),
        "currency": meta.get("currency", "USD"),
        "market_state": meta.get("marketState", "LIVE"),
        "current_price": round(last_price, 2),
        "previous_close": round(prev_close, 2),
        "day_change": round(day_change, 2),
        "day_change_pct": round(day_change_pct, 2),
        "day_high": round(float(meta.get("regularMarketDayHigh") or last_price), 2),
        "day_low": round(float(meta.get("regularMarketDayLow") or last_price), 2),
        "volume": int(meta.get("regularMarketVolume") or 0),
        "data_source": "REAL_MARKET",
        "is_simulated": False,
        "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
    if include_intraday:
        quote["intraday"] = intraday_bars
    return quote


def fetch_real_time_quotes(symbols: list[str] | None = None) -> dict:
    target_symbols = [s.strip().upper() for s in (symbols or list(SUPPORTED_REAL_TICKERS.keys()))]
    quotes = []
    errors = []

    def _safe_fetch(sym: str):
        try:
            return fetch_real_time_quote(sym, include_intraday=False), None
        except MarketDataUnavailableError as exc:
            return None, {"symbol": sym, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=6) as pool:
        for q, err in pool.map(_safe_fetch, target_symbols):
            if q:
                quotes.append(q)
            if err:
                errors.append(err)

    return {
        "quotes": quotes,
        "errors": errors,
        "available": len(quotes) > 0,
        "data_source": "REAL_MARKET",
        "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }

