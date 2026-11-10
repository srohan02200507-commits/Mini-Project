from datetime import date, timedelta
import numpy as np
import pandas as pd

from app.extensions import db
from app.models import MarketData, Stock


SIMULATED_STOCK_CATALOG = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc. (Simulated)",
        "sector": "Technology",
        "market_cap_tier": "Mega Cap",
        "base_price": 192.0,
        "base_volatility": 0.23,
        "drift_bias": 0.11,
        "description": "Simulated consumer hardware & software ecosystem stock used for educational trend modeling.",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corp. (Simulated)",
        "sector": "Technology",
        "market_cap_tier": "Mega Cap",
        "base_price": 415.0,
        "base_volatility": 0.21,
        "drift_bias": 0.12,
        "description": "Simulated enterprise cloud and AI software leader with steady trend characteristics.",
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corp. (Simulated)",
        "sector": "Semiconductors",
        "market_cap_tier": "Mega Cap",
        "base_price": 124.0,
        "base_volatility": 0.42,
        "drift_bias": 0.18,
        "description": "Simulated high-beta semiconductor and AI compute asset with elevated volatility.",
    },
    {
        "symbol": "TSLA",
        "name": "Tesla Inc. (Simulated)",
        "sector": "Automotive & Energy",
        "market_cap_tier": "Large Cap",
        "base_price": 248.0,
        "base_volatility": 0.48,
        "drift_bias": 0.08,
        "description": "Simulated EV and clean-energy growth equity exhibiting wide price swings for risk studies.",
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc. (Simulated)",
        "sector": "Consumer Discretionary",
        "market_cap_tier": "Mega Cap",
        "base_price": 186.0,
        "base_volatility": 0.27,
        "drift_bias": 0.11,
        "description": "Simulated e-commerce and cloud infrastructure giant with cyclical momentum patterns.",
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc. (Simulated)",
        "sector": "Communication Services",
        "market_cap_tier": "Mega Cap",
        "base_price": 168.0,
        "base_volatility": 0.25,
        "drift_bias": 0.10,
        "description": "Simulated digital advertising and AI research equity for momentum and mean-reversion tests.",
    },
    {
        "symbol": "JPM",
        "name": "JPMorgan Chase (Simulated)",
        "sector": "Financials",
        "market_cap_tier": "Large Cap",
        "base_price": 205.0,
        "base_volatility": 0.20,
        "drift_bias": 0.09,
        "description": "Simulated diversified financial institution representing interest-rate sensitive banking.",
    },
    {
        "symbol": "JNJ",
        "name": "Johnson & Johnson (Simulated)",
        "sector": "Healthcare",
        "market_cap_tier": "Large Cap",
        "base_price": 156.0,
        "base_volatility": 0.15,
        "drift_bias": 0.06,
        "description": "Simulated defensive healthcare stock with lower historical volatility and drawdown.",
    },
    {
        "symbol": "XOM",
        "name": "Exxon Mobil Corp. (Simulated)",
        "sector": "Energy",
        "market_cap_tier": "Large Cap",
        "base_price": 114.0,
        "base_volatility": 0.24,
        "drift_bias": 0.07,
        "description": "Simulated integrated energy equity reflecting commodity-linked price cycles.",
    },
    {
        "symbol": "SPY",
        "name": "S&P 500 ETF (Simulated)",
        "sector": "Broad Market Index",
        "market_cap_tier": "Index ETF",
        "base_price": 532.0,
        "base_volatility": 0.14,
        "drift_bias": 0.09,
        "description": "Simulated broad-market benchmark ETF useful for comparing single-stock volatility and risk.",
    },
]


def next_trading_day(current_date: date) -> date:
    candidate = current_date + timedelta(days=1)
    while candidate.weekday() >= 5:  # Skip Saturday (5) and Sunday (6)
        candidate += timedelta(days=1)
    return candidate


def get_trading_days_back(end_date: date, count: int) -> list[date]:
    days = []
    cur = end_date
    while len(days) < count:
        if cur.weekday() < 5:
            days.append(cur)
        cur -= timedelta(days=1)
    days.reverse()
    return days


def get_stock_dataframe(stock_id: int, limit: int | None = None) -> pd.DataFrame:
    query = MarketData.query.filter_by(stock_id=stock_id).order_by(MarketData.date.asc())
    rows = query.all()
    if limit and len(rows) > limit:
        rows = rows[-limit:]

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "date": r.date,
                "open": float(r.open_price),
                "high": float(r.high_price),
                "low": float(r.low_price),
                "close": float(r.close_price),
                "volume": int(r.volume),
            }
            for r in rows
        ]
    )
    return df


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    data = df.copy()
    close = data["close"]

    data["return_1d"] = close.pct_change()
    data["return_3d"] = close.pct_change(3)
    data["return_5d"] = close.pct_change(5)
    data["return_10d"] = close.pct_change(10)

    data["sma_5"] = close.rolling(window=5).mean()
    data["sma_10"] = close.rolling(window=10).mean()
    data["sma_20"] = close.rolling(window=20).mean()
    data["sma_50"] = close.rolling(window=50).mean()

    data["ema_12"] = close.ewm(span=12, adjust=False).mean()
    data["ema_26"] = close.ewm(span=26, adjust=False).mean()
    data["macd"] = data["ema_12"] - data["ema_26"]
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
    data["macd_hist"] = data["macd"] - data["macd_signal"]

    # RSI-14 using Wilder-style exponential smoothing
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    data["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))
    data["rsi_14"] = data["rsi_14"].fillna(50.0)

    # Bollinger Bands (20-day, 2 std)
    bb_std = close.rolling(window=20).std()
    data["bb_mid"] = data["sma_20"]
    data["bb_upper"] = data["bb_mid"] + (2.0 * bb_std)
    data["bb_lower"] = data["bb_mid"] - (2.0 * bb_std)
    band_width = (data["bb_upper"] - data["bb_lower"]).replace(0.0, np.nan)
    data["bb_pct"] = (close - data["bb_lower"]) / band_width

    # Volatility & volume signals
    data["volatility_20"] = data["return_1d"].rolling(window=20).std() * np.sqrt(252) * 100.0
    vol_ma_20 = data["volume"].rolling(window=20).mean().replace(0.0, np.nan)
    data["volume_ratio"] = data["volume"] / vol_ma_20

    # Relative ratios for scale-invariant ML features
    data["price_vs_sma5"] = (close - data["sma_5"]) / data["sma_5"].replace(0.0, np.nan)
    data["price_vs_sma20"] = (close - data["sma_20"]) / data["sma_20"].replace(0.0, np.nan)
    data["sma5_vs_sma20"] = (data["sma_5"] - data["sma_20"]) / data["sma_20"].replace(0.0, np.nan)
    data["hl_spread_pct"] = (data["high"] - data["low"]) / close.replace(0.0, np.nan)

    return data


def generate_simulated_ohlcv_series(
    base_price: float,
    base_volatility: float,
    drift_bias: float,
    dates: list[date],
    rng: np.random.Generator,
) -> list[dict]:
    records = []
    price = float(base_price)
    dt = 1.0 / 252.0
    regime_momentum = 0.0

    for idx, d in enumerate(dates):
        # Smoothly evolving simulated market cycle + mean-reverting momentum
        cycle = 0.0008 * np.sin(idx / 11.0)
        shock = rng.normal(0.0, 1.0)
        regime_momentum = 0.65 * regime_momentum + 0.35 * (shock * 0.004)
        daily_drift = (drift_bias * dt) + cycle + regime_momentum
        daily_vol = base_volatility * np.sqrt(dt)
        ret = daily_drift + daily_vol * shock
        ret = float(np.clip(ret, -0.085, 0.085))

        open_p = price * (1.0 + float(rng.normal(0.0, 0.0025)))
        close_p = max(5.0, price * (1.0 + ret))
        intraday_spread = abs(ret) + abs(float(rng.normal(0.0, daily_vol * 0.6)))
        high_p = max(open_p, close_p) * (1.0 + intraday_spread * 0.45)
        low_p = max(1.0, min(open_p, close_p) * (1.0 - intraday_spread * 0.45))
        base_vol = 2_800_000 if base_price < 300 else 1_600_000
        volume = int(base_vol * (1.0 + min(2.5, abs(ret) * 35.0) + abs(float(rng.normal(0.0, 0.25)))))

        records.append(
            {
                "date": d,
                "open_price": round(open_p, 2),
                "high_price": round(high_p, 2),
                "low_price": round(low_p, 2),
                "close_price": round(close_p, 2),
                "volume": max(150_000, volume),
            }
        )
        price = close_p

    return records


def advance_simulated_market(days: int = 1) -> list[date]:
    days = max(1, min(int(days), 30))
    stocks = Stock.query.order_by(Stock.symbol.asc()).all()
    if not stocks:
        return []

    generated_dates = []
    rng = np.random.default_rng()

    for _ in range(days):
        # Shared macro factor so simulated stocks exhibit realistic market co-movement
        macro_shock = float(rng.normal(0.0005, 0.006))
        step_date = next_trading_day(stocks[0].last_updated_date)
        generated_dates.append(step_date)

        for stock in stocks:
            recent_bars = (
                MarketData.query.filter_by(stock_id=stock.id)
                .order_by(MarketData.date.desc())
                .limit(6)
                .all()
            )
            recent_momentum = 0.0
            if len(recent_bars) >= 5:
                recent_momentum = (recent_bars[0].close_price - recent_bars[4].close_price) / recent_bars[4].close_price
                recent_momentum = float(np.clip(recent_momentum * 0.08, -0.008, 0.008))

            dt = 1.0 / 252.0
            idio_shock = float(rng.normal(0.0, 1.0)) * (stock.base_volatility * np.sqrt(dt))
            ret = (stock.drift_bias * dt) + (0.65 * macro_shock) + recent_momentum + idio_shock
            ret = float(np.clip(ret, -0.08, 0.08))

            prev_close = float(stock.current_price)
            open_p = prev_close * (1.0 + float(rng.normal(0.0, 0.002)))
            close_p = max(5.0, prev_close * (1.0 + ret))
            spread = abs(ret) + abs(float(rng.normal(0.0, stock.base_volatility * np.sqrt(dt) * 0.55)))
            high_p = max(open_p, close_p) * (1.0 + spread * 0.45)
            low_p = max(1.0, min(open_p, close_p) * (1.0 - spread * 0.45))

            avg_vol = int(np.mean([b.volume for b in recent_bars])) if recent_bars else 2_000_000
            volume = int(avg_vol * (0.85 + min(2.0, abs(ret) * 30.0) + abs(float(rng.normal(0.0, 0.2)))))

            bar = MarketData(
                stock_id=stock.id,
                date=step_date,
                open_price=round(open_p, 2),
                high_price=round(high_p, 2),
                low_price=round(low_p, 2),
                close_price=round(close_p, 2),
                volume=max(150_000, volume),
                is_simulated=True,
            )
            db.session.add(bar)

            stock.previous_close = round(prev_close, 2)
            stock.current_price = round(close_p, 2)
            stock.day_change_pct = round(((close_p - prev_close) / prev_close) * 100.0, 2) if prev_close > 0 else 0.0
            stock.last_updated_date = step_date

    db.session.commit()
    return generated_dates

