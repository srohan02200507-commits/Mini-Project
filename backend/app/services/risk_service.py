import numpy as np
import pandas as pd

from app.models import Stock, User, VirtualPortfolio
from app.services.market_service import get_stock_dataframe


def _risk_rating(annual_vol_pct: float, max_drawdown_pct: float) -> tuple[str, str]:
    if annual_vol_pct < 18.0 and abs(max_drawdown_pct) < 12.0:
        return (
            "Low",
            "Relatively steady simulated price swings compared to single growth equities. Still subject to market downturns.",
        )
    if annual_vol_pct < 28.0 and abs(max_drawdown_pct) < 20.0:
        return (
            "Moderate",
            "Balanced volatility profile suitable for learning trend dynamics while maintaining position sizing discipline.",
        )
    if annual_vol_pct < 40.0:
        return (
            "Elevated",
            "Noticeable daily swings and drawdown potential. Smaller position sizes and diversification help limit risk.",
        )
    return (
        "High",
        "High historical volatility and sharp swing risk. Large drawdowns can happen rapidly without guarantees of recovery.",
    )


def analyze_stock_risk(stock: Stock, benchmark_df: pd.DataFrame | None = None) -> dict:
    df = get_stock_dataframe(stock.id)
    if df.empty or len(df) < 15:
        return {
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "current_price": round(stock.current_price, 2),
            "annualized_volatility_pct": round(stock.base_volatility * 100.0, 2),
            "recent_30d_volatility_pct": round(stock.base_volatility * 100.0, 2),
            "value_at_risk_95_pct": 2.5,
            "max_drawdown_pct": -8.0,
            "beta_vs_spy": 1.0,
            "risk_adjusted_ratio": 0.4,
            "risk_level": "Moderate",
            "risk_summary": "Limited history available; showing baseline parameters.",
            "series": [],
        }

    close = df["close"].astype(float)
    returns = close.pct_change().dropna()

    annual_vol = float(returns.std() * np.sqrt(252) * 100.0)
    vol_30d = float(returns.tail(30).std() * np.sqrt(252) * 100.0) if len(returns) >= 10 else annual_vol
    var_95 = float(abs(np.percentile(returns, 5)) * 100.0)

    running_peak = close.cummax()
    drawdown_series = ((close - running_peak) / running_peak) * 100.0
    max_drawdown = float(drawdown_series.min())

    mean_annual_ret = float(returns.mean() * 252.0)
    annual_vol_dec = max(0.01, annual_vol / 100.0)
    sharpe_like = float((mean_annual_ret - 0.03) / annual_vol_dec)

    beta = 1.0
    if stock.symbol != "SPY" and benchmark_df is not None and not benchmark_df.empty:
        merged = pd.merge(
            df[["date", "close"]],
            benchmark_df[["date", "close"]].rename(columns={"close": "bench_close"}),
            on="date",
            how="inner",
        )
        if len(merged) > 20:
            r_stock = merged["close"].pct_change().dropna()
            r_bench = merged["bench_close"].pct_change().dropna()
            var_b = float(np.var(r_bench))
            if var_b > 1e-10:
                cov = float(np.cov(r_stock, r_bench)[0, 1])
                beta = round(cov / var_b, 2)

    risk_level, risk_summary = _risk_rating(annual_vol, max_drawdown)

    rolling_vol_20 = (returns.rolling(window=20).std() * np.sqrt(252) * 100.0).fillna(annual_vol)
    tail_df = df.tail(60).copy()
    tail_dd = drawdown_series.tail(60).values
    tail_vol = rolling_vol_20.reindex(tail_df.index).fillna(annual_vol).values

    series = []
    for idx, row in enumerate(tail_df.itertuples()):
        series.append(
            {
                "date": row.date.isoformat(),
                "close": round(float(row.close), 2),
                "volatility_pct": round(float(tail_vol[idx]), 2),
                "drawdown_pct": round(float(tail_dd[idx]), 2),
            }
        )

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "current_price": round(float(stock.current_price), 2),
        "annualized_volatility_pct": round(annual_vol, 2),
        "recent_30d_volatility_pct": round(vol_30d, 2),
        "value_at_risk_95_pct": round(var_95, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "beta_vs_spy": round(beta, 2),
        "risk_adjusted_ratio": round(sharpe_like, 2),
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "series": series,
    }


def build_risk_overview(user: User | None = None, focus_symbol: str | None = None) -> dict:
    stocks = Stock.query.order_by(Stock.symbol.asc()).all()
    spy_stock = next((s for s in stocks if s.symbol == "SPY"), None)
    spy_df = get_stock_dataframe(spy_stock.id) if spy_stock else None

    stock_risks = [analyze_stock_risk(s, benchmark_df=spy_df) for s in stocks]
    risk_by_symbol = {r["symbol"]: r for r in stock_risks}

    selected = risk_by_symbol.get((focus_symbol or "NVDA").upper(), stock_risks[0] if stock_risks else None)

    portfolio_risk = {
        "has_positions": False,
        "diversification_score": 100,
        "weighted_volatility_pct": 0.0,
        "largest_position_pct": 0.0,
        "cash_buffer_pct": 100.0,
        "warnings": ["No virtual positions held yet. Virtual cash is 100% uninvested."],
    }

    if user is not None:
        holdings = VirtualPortfolio.query.filter_by(user_id=user.id).all()
        cash = float(user.virtual_cash_balance)

        def _holding_price(h: VirtualPortfolio) -> float:
            if h.data_source == "SIMULATED_TEST" and h.stock:
                return float(h.stock.current_price)
            return float(h.last_known_price)

        invested = sum(h.quantity * _holding_price(h) for h in holdings)
        total_equity = cash + invested

        if holdings and invested > 0 and total_equity > 0:
            weights_invested = []
            weighted_vol = 0.0
            max_equity_share = 0.0
            max_symbol = ""
            sectors = set()

            for h in holdings:
                val = h.quantity * _holding_price(h)
                w_inv = val / invested
                w_eq = val / total_equity
                sym_vol = risk_by_symbol.get(h.stock_symbol, {}).get("annualized_volatility_pct", 25.0)
                weighted_vol += w_inv * sym_vol
                weights_invested.append(w_inv)
                sectors.add(h.sector or "Equities")
                if w_eq > max_equity_share:
                    max_equity_share = w_eq
                    max_symbol = h.stock_symbol

            hhi = sum(w * w for w in weights_invested)
            div_score = round(max(15.0, min(100.0, (1.0 - hhi) * 115.0 + len(sectors) * 5.0)), 1)
            cash_pct = round((cash / total_equity) * 100.0, 1)
            largest_pct = round(max_equity_share * 100.0, 1)

            warnings = []
            if len(holdings) < 3:
                warnings.append(
                    f"Low diversification: only {len(holdings)} holding(s). Consider spreading virtual practice across multiple sectors."
                )
            if largest_pct > 35.0:
                warnings.append(
                    f"Concentration alert: {max_symbol} represents {largest_pct:.1f}% of total virtual equity."
                )
            if weighted_vol > 32.0:
                warnings.append(
                    f"Elevated portfolio volatility ({weighted_vol:.1f}% annualized) due to high-beta holdings."
                )
            if not warnings:
                warnings.append("Virtual portfolio shows balanced diversification across holdings and cash reserves.")

            portfolio_risk = {
                "has_positions": True,
                "diversification_score": div_score,
                "weighted_volatility_pct": round(weighted_vol, 2),
                "largest_position_pct": largest_pct,
                "largest_position_symbol": max_symbol,
                "cash_buffer_pct": cash_pct,
                "sectors_count": len(sectors),
                "warnings": warnings,
            }

    educational_guides = [
        {
            "title": "Historical Volatility (Annualized)",
            "explanation": "Measures how widely a stock's daily prices swing, scaled to a 252-trading-day year. Higher volatility means both larger potential upswings and sharper drops.",
        },
        {
            "title": "Value at Risk (95% 1-Day VaR)",
            "explanation": "Estimates the daily loss threshold that was only exceeded in the worst 5% of historical days. It is a statistical estimate, never a worst-case ceiling.",
        },
        {
            "title": "Maximum Drawdown",
            "explanation": "Shows the largest peak-to-trough percentage drop during the recorded historical period, illustrating downside stress.",
        },
        {
            "title": "No Profit Guarantees",
            "explanation": "AI predictions and risk scores analyze historical patterns. No model can guarantee profits, eliminate loss risk, or predict sudden news shocks.",
        },
    ]

    return {
        "selected_stock_risk": selected,
        "all_stocks_risk": [{k: v for k, v in item.items() if k != "series"} for item in stock_risks],
        "portfolio_risk": portfolio_risk,
        "educational_guides": educational_guides,
        "is_simulated": True,
        "disclaimer": (
            "Risk metrics are provided for educational awareness only. "
            "TradeWise AI does not guarantee profits or returns."
        ),
    }
