from datetime import datetime, time

from flask import Blueprint, jsonify, request

from app.models import Prediction, Stock
from app.services.accountability_service import verify_all_due_predictions
from app.services.market_provider import (
    SUPPORTED_REAL_TICKERS,
    MarketDataUnavailableError,
    fetch_real_time_quote,
    fetch_real_time_quotes,
    get_market_series,
)
from app.services.market_service import advance_simulated_market, compute_technical_indicators
from app.utils.auth import token_required

market_bp = Blueprint("market", __name__, url_prefix="/api/market")


@market_bp.get("/stocks")
def list_stocks():
    data_source = (request.args.get("data_source") or "SIMULATED_TEST").strip().upper()

    if data_source == "REAL_MARKET":
        symbols = list(SUPPORTED_REAL_TICKERS.keys())
        live = fetch_real_time_quotes(symbols)
        enriched = []
        for q in live["quotes"]:
            latest_pred = (
                Prediction.query.filter_by(stock_symbol=q["symbol"])
                .order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
                .first()
            )
            q["latest_prediction"] = latest_pred.to_dict() if latest_pred else None
            enriched.append(q)

        sorted_by_chg = sorted(enriched, key=lambda x: x["day_change_pct"], reverse=True)
        return jsonify(
            {
                "stocks": enriched,
                "top_gainers": sorted_by_chg[:3],
                "top_losers": list(reversed(sorted_by_chg[-3:])) if len(sorted_by_chg) >= 3 else sorted_by_chg,
                "data_source": "REAL_MARKET",
                "is_simulated": False,
                "available": live["available"],
                "errors": live["errors"],
                "fetched_at": live["fetched_at"],
            }
        ), 200

    stocks = Stock.query.order_by(Stock.symbol.asc()).all()
    stock_dicts = []
    for s in stocks:
        latest_pred = (
            Prediction.query.filter_by(stock_symbol=s.symbol)
            .order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
            .first()
        )
        d = s.to_dict()
        d["latest_prediction"] = latest_pred.to_dict() if latest_pred else None
        stock_dicts.append(d)

    sorted_by_change = sorted(stock_dicts, key=lambda x: x["day_change_pct"], reverse=True)
    current_date = stocks[0].last_updated_date.isoformat() if stocks else None

    return jsonify(
        {
            "stocks": stock_dicts,
            "top_gainers": sorted_by_change[:3],
            "top_losers": list(reversed(sorted_by_change[-3:])),
            "current_simulated_date": current_date,
            "data_source": "SIMULATED_TEST",
            "is_simulated": True,
            "disclaimer": "All simulated testing prices are strictly separated from real market data.",
        }
    ), 200


@market_bp.get("/live-quotes")
def live_quotes():
    raw_symbols = (request.args.get("symbols") or "").strip()
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()] if raw_symbols else None
    payload = fetch_real_time_quotes(symbols)
    if not payload["available"]:
        return jsonify(
            {
                **payload,
                "error": "Live market quotes are currently unreachable.",
            }
        ), 503
    return jsonify(payload), 200


@market_bp.get("/live-quote/<symbol>")
def live_quote_detail(symbol: str):
    include_intraday = request.args.get("intraday", default="true").lower() == "true"
    try:
        quote = fetch_real_time_quote(symbol, include_intraday=include_intraday)
        return jsonify(quote), 200
    except MarketDataUnavailableError as exc:
        return jsonify({"error": str(exc), "available": False}), 503


@market_bp.get("/stocks/<symbol>")
def get_stock_detail(symbol: str):
    clean_symbol = symbol.strip().upper()
    data_source = (request.args.get("data_source") or "REAL_MARKET").strip().upper()
    days = request.args.get("days", default=90, type=int)
    days = max(20, min(days or 90, 365))

    try:
        stock_meta, full_df = get_market_series(clean_symbol, data_source=data_source)
    except MarketDataUnavailableError as exc:
        return jsonify({"error": str(exc), "data_source": data_source}), 503

    ind_df = compute_technical_indicators(full_df)
    sliced = ind_df.tail(days)

    history = []
    for row in sliced.itertuples():
        history.append(
            {
                "date": row.date.isoformat(),
                "open": round(float(row.open), 2),
                "high": round(float(row.high), 2),
                "low": round(float(row.low), 2),
                "close": round(float(row.close), 2),
                "volume": int(row.volume),
                "sma_5": round(float(row.sma_5), 2) if row.sma_5 == row.sma_5 else None,
                "sma_20": round(float(row.sma_20), 2) if row.sma_20 == row.sma_20 else None,
                "sma_50": round(float(row.sma_50), 2) if row.sma_50 == row.sma_50 else None,
                "rsi_14": round(float(row.rsi_14), 2) if row.rsi_14 == row.rsi_14 else None,
                "macd": round(float(row.macd), 3) if row.macd == row.macd else None,
                "macd_signal": round(float(row.macd_signal), 3) if row.macd_signal == row.macd_signal else None,
                "bb_upper": round(float(row.bb_upper), 2) if row.bb_upper == row.bb_upper else None,
                "bb_lower": round(float(row.bb_lower), 2) if row.bb_lower == row.bb_lower else None,
            }
        )

    latest = ind_df.iloc[-1]
    latest_pred = (
        Prediction.query.filter_by(stock_symbol=clean_symbol)
        .order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
        .first()
    )

    return jsonify(
        {
            "stock": stock_meta,
            "history": history,
            "indicators": {
                "rsi_14": round(float(latest.get("rsi_14", 50.0)), 2),
                "sma_5": round(float(latest.get("sma_5", stock_meta["current_price"])), 2),
                "sma_20": round(float(latest.get("sma_20", stock_meta["current_price"])), 2),
                "sma_50": round(float(latest.get("sma_50", stock_meta["current_price"])), 2),
                "macd": round(float(latest.get("macd", 0.0)), 3),
                "macd_signal": round(float(latest.get("macd_signal", 0.0)), 3),
                "volatility_20": round(float(latest.get("volatility_20", 20.0) or 20.0), 2),
                "return_5d_pct": round(float(latest.get("return_5d", 0.0) or 0.0) * 100.0, 2),
            },
            "latest_prediction": latest_pred.to_dict() if latest_pred else None,
            "data_source": stock_meta.get("data_source", data_source),
            "is_simulated": bool(stock_meta.get("is_simulated", data_source == "SIMULATED_TEST")),
        }
    ), 200


@market_bp.post("/simulate-day")
@token_required
def simulate_next_day():
    data = request.get_json(silent=True) or {}
    days = data.get("days", 1)
    try:
        days = int(days)
    except (TypeError, ValueError):
        return jsonify({"error": "days must be an integer between 1 and 10."}), 400

    if days < 1 or days > 10:
        return jsonify({"error": "days must be between 1 and 10."}), 400

    generated_dates = advance_simulated_market(days=days)
    sim_clock = (
        datetime.combine(generated_dates[-1], time(23, 59))
        if generated_dates
        else None
    )
    eval_summary = verify_all_due_predictions(data_source="SIMULATED_TEST", now=sim_clock)

    return jsonify(
        {
            "message": (
                f"Simulated {len(generated_dates)} trading day(s) and verified "
                f"{eval_summary['verified_count']} due simulated prediction(s)."
            ),
            "generated_dates": [d.isoformat() for d in generated_dates],
            "evaluated_predictions": eval_summary["verified_count"],
            "current_simulated_date": generated_dates[-1].isoformat() if generated_dates else None,
        }
    ), 200
