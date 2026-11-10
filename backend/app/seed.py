from datetime import date, datetime, time, timezone
import numpy as np

from app.extensions import db
from app.models import ChatHistory, MarketData, Prediction, Stock, Transaction, User, VirtualPortfolio
from app.services.accountability_service import generate_prediction_id, verify_single_prediction
from app.services.market_service import (
    SIMULATED_STOCK_CATALOG,
    generate_simulated_ohlcv_series,
    get_stock_dataframe,
    get_trading_days_back,
)
from app.services.ml_engine import run_ml_prediction_from_df, serialize_json_list


def seed_database(force_backtest: bool = True) -> None:
    """Populate simulated testing catalog, demo student account, and immutable historical walk-forward predictions."""
    if Stock.query.first() is not None:
        return

    rng = np.random.default_rng(2026)
    end_date = date(2026, 11, 10)
    trading_days = get_trading_days_back(end_date, 165)

    created_stocks = []
    for item in SIMULATED_STOCK_CATALOG:
        bars = generate_simulated_ohlcv_series(
            base_price=item["base_price"],
            base_volatility=item["base_volatility"],
            drift_bias=item["drift_bias"],
            dates=trading_days,
            rng=rng,
        )
        latest = bars[-1]
        prev = bars[-2]
        day_change_pct = ((latest["close_price"] - prev["close_price"]) / prev["close_price"]) * 100.0

        stock = Stock(
            symbol=item["symbol"],
            name=item["name"],
            sector=item["sector"],
            market_cap_tier=item["market_cap_tier"],
            description=item["description"],
            base_volatility=item["base_volatility"],
            drift_bias=item["drift_bias"],
            current_price=latest["close_price"],
            previous_close=prev["close_price"],
            day_change_pct=round(day_change_pct, 2),
            is_simulated=True,
            last_updated_date=latest["date"],
        )
        db.session.add(stock)
        db.session.flush()

        for bar in bars:
            db.session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar["date"],
                    open_price=bar["open_price"],
                    high_price=bar["high_price"],
                    low_price=bar["low_price"],
                    close_price=bar["close_price"],
                    volume=bar["volume"],
                    is_simulated=True,
                )
            )
        created_stocks.append(stock)

    demo_user = User.query.filter_by(username="demo").first()
    if demo_user is None:
        demo_user = User(
            username="demo",
            email="demo@tradewise.edu",
            full_name="Alex Rivera (Demo)",
            experience_level="beginner",
            virtual_cash_balance=100000.0,
            initial_cash_balance=100000.0,
        )
        demo_user.set_password("demo1234")
        db.session.add(demo_user)
        db.session.flush()

        starter_allocations = [("AAPL", 30), ("MSFT", 15), ("SPY", 20)]
        for sym, qty in starter_allocations:
            st = next((s for s in created_stocks if s.symbol == sym), None)
            if st:
                cost_price = round(st.current_price * 0.97, 2)
                total = round(cost_price * qty, 2)
                demo_user.virtual_cash_balance = round(demo_user.virtual_cash_balance - total, 2)
                db.session.add(
                    VirtualPortfolio(
                        user_id=demo_user.id,
                        stock_id=st.id,
                        stock_symbol=st.symbol,
                        stock_name=st.name,
                        sector=st.sector,
                        data_source="SIMULATED_TEST",
                        quantity=float(qty),
                        average_buy_price=cost_price,
                        last_known_price=st.current_price,
                    )
                )
                db.session.add(
                    Transaction(
                        user_id=demo_user.id,
                        stock_id=st.id,
                        stock_symbol=st.symbol,
                        stock_name=st.name,
                        data_source="SIMULATED_TEST",
                        transaction_type="BUY",
                        quantity=float(qty),
                        price_per_share=cost_price,
                        total_amount=total,
                        realized_pnl=None,
                        notes=f"Initial simulated demo allocation ({qty} {sym})",
                        is_simulated=True,
                    )
                )

        db.session.add(
            ChatHistory(
                user_id=demo_user.id,
                role="assistant",
                message=(
                    "Welcome to **TradeWise AI**! Explore the **Prediction Accountability Engine**, "
                    "compare Predicted vs Actual prices, test **Real-Time Virtual Trading**, or ask me why any forecast was generated."
                ),
                context_symbol="AAPL",
                intent="welcome",
            )
        )

    db.session.commit()

    if force_backtest:
        backtest_offsets = [-40, -34, -27, -20, -14, -8, -3]
        backtest_stocks = created_stocks[:6]

        for stock in backtest_stocks:
            full_df = get_stock_dataframe(stock.id)
            for offset in backtest_offsets:
                slice_end = len(full_df) + offset
                if slice_end < 80:
                    continue
                sub_df = full_df.iloc[:slice_end].copy()
                last_dt = sub_df.iloc[-1]["date"]
                pred_ts = datetime.combine(last_dt, time(9, 30))
                try:
                    forecast = run_ml_prediction_from_df(
                        sub_df,
                        horizon_days=1,
                        tolerance_pct=0.50,
                        prediction_timestamp=pred_ts,
                    )
                except ValueError:
                    continue

                pred = Prediction(
                    prediction_id=generate_prediction_id(pred_ts),
                    user_id=None,
                    stock_id=stock.id,
                    stock_symbol=stock.symbol,
                    stock_name=stock.name,
                    starting_price=forecast["starting_price"],
                    predicted_price=forecast["predicted_price"],
                    predicted_return_pct=forecast["predicted_return_pct"],
                    predicted_direction=forecast["predicted_direction"],
                    prediction_timestamp=forecast["prediction_timestamp"],
                    target_timestamp=forecast["target_timestamp"],
                    confidence_score=forecast["confidence_score"],
                    model_name=forecast["model_name"],
                    model_version=forecast["model_version"],
                    horizon_label=forecast["horizon_label"],
                    prediction_reason=forecast["prediction_reason"],
                    historical_patterns_json=serialize_json_list(forecast["historical_patterns"]),
                    confidence_meaning=forecast["confidence_meaning"],
                    invalidation_factors_json=serialize_json_list(forecast["invalidation_factors"]),
                    verification_status="PENDING VERIFICATION",
                    prediction_result="PENDING",
                    tolerance_pct=forecast["tolerance_pct"],
                    data_source="SIMULATED_TEST",
                    is_simulated=True,
                )
                db.session.add(pred)

        db.session.commit()

        # Verify historical walk-forward predictions against actual simulated bars (using end_date + 1 day as eval clock)
        eval_clock = datetime(2026, 11, 11, 16, 0)
        for pred in Prediction.query.filter_by(verification_status="PENDING VERIFICATION").all():
            verify_single_prediction(pred, now=eval_clock)

        # Add 3 active PENDING VERIFICATION forecasts for the latest simulated date
        for stock in created_stocks[:3]:
            full_df = get_stock_dataframe(stock.id)
            last_dt = full_df.iloc[-1]["date"]
            pred_ts = datetime.combine(last_dt, time(16, 0))
            try:
                forecast = run_ml_prediction_from_df(
                    full_df,
                    horizon_days=1,
                    tolerance_pct=0.50,
                    prediction_timestamp=pred_ts,
                )
            except ValueError:
                continue

            db.session.add(
                Prediction(
                    prediction_id=generate_prediction_id(pred_ts),
                    user_id=None,
                    stock_id=stock.id,
                    stock_symbol=stock.symbol,
                    stock_name=stock.name,
                    starting_price=forecast["starting_price"],
                    predicted_price=forecast["predicted_price"],
                    predicted_return_pct=forecast["predicted_return_pct"],
                    predicted_direction=forecast["predicted_direction"],
                    prediction_timestamp=forecast["prediction_timestamp"],
                    target_timestamp=forecast["target_timestamp"],
                    confidence_score=forecast["confidence_score"],
                    model_name=forecast["model_name"],
                    model_version=forecast["model_version"],
                    horizon_label=forecast["horizon_label"],
                    prediction_reason=forecast["prediction_reason"],
                    historical_patterns_json=serialize_json_list(forecast["historical_patterns"]),
                    confidence_meaning=forecast["confidence_meaning"],
                    invalidation_factors_json=serialize_json_list(forecast["invalidation_factors"]),
                    verification_status="PENDING VERIFICATION",
                    prediction_result="PENDING",
                    tolerance_pct=forecast["tolerance_pct"],
                    data_source="SIMULATED_TEST",
                    is_simulated=True,
                )
            )
        db.session.commit()
