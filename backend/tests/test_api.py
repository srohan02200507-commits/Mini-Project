from datetime import date, datetime, timedelta
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import (
    ChatHistory,
    MarketData,
    Prediction,
    PredictionResult,
    Stock,
    Transaction,
    User,
    VirtualPortfolio,
)
from app.services.accountability_service import (
    compute_accountability_dashboard,
    generate_prediction_id,
    verify_single_prediction,
)
from app.services.ml_engine import run_ml_prediction_from_df, serialize_json_list


@pytest.fixture(scope="module")
def app_instance():
    app = create_app(config_object=TestConfig, auto_seed=True, force_backtest=False)
    return app


@pytest.fixture(scope="module")
def client(app_instance):
    with app_instance.test_client() as test_client:
        yield test_client


def _register_and_get_headers(client, username="trader1", email="trader1@example.com"):
    res = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "Password123!",
            "full_name": "Test Trader",
            "experience_level": "beginner",
        },
    )
    assert res.status_code == 201
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _build_synthetic_ohlcv(trend: str, length: int = 120) -> pd.DataFrame:
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(length)]
    closes = []
    price = 150.0
    for i in range(length):
        if trend == "UP":
            price = price * 1.0085 + (0.08 if i % 2 == 0 else 0.02)
        elif trend == "DOWN":
            price = price * 0.9915 - (0.08 if i % 2 == 0 else 0.02)
        else:  # SIDEWAYS
            price = 150.0 + (0.12 if i % 2 == 0 else -0.12)
        closes.append(round(price, 2))

    return pd.DataFrame(
        [
            {
                "timestamp": datetime.combine(d, datetime.min.time()),
                "date": d,
                "open": c,
                "high": round(c * 1.004, 2),
                "low": round(c * 0.996, 2),
                "close": c,
                "volume": 2_000_000 + i * 1000,
            }
            for i, (d, c) in enumerate(zip(dates, closes))
        ]
    )


def _create_isolated_stock(symbol: str, base_price: float = 200.0) -> Stock:
    existing = Stock.query.filter_by(symbol=symbol).first()
    if existing:
        return existing
    s = Stock(
        symbol=symbol,
        name=f"{symbol} Test Corp",
        sector="Technology",
        market_cap_tier="Large Cap",
        description="Isolated test equity",
        base_volatility=0.20,
        drift_bias=0.05,
        current_price=base_price,
        previous_close=base_price,
        day_change_pct=0.0,
        is_simulated=True,
        last_updated_date=date(2026, 10, 1),
    )
    db.session.add(s)
    db.session.flush()
    for i in range(100):
        d = date(2026, 6, 1) + timedelta(days=i)
        c = round(base_price + (i * 0.4), 2)
        db.session.add(
            MarketData(
                stock_id=s.id,
                date=d,
                open_price=c,
                high_price=round(c + 1.0, 2),
                low_price=round(c - 1.0, 2),
                close_price=c,
                volume=1_500_000,
                is_simulated=True,
            )
        )
        s.last_updated_date = d
        s.current_price = c
    db.session.commit()
    return s


def test_seeded_tables_and_auth(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"

    with client.application.app_context():
        assert Stock.query.count() == 10
        assert MarketData.query.count() >= 1600
        assert User.query.filter_by(username="demo").first() is not None
        assert VirtualPortfolio.query.count() >= 1
        assert Transaction.query.count() >= 1
        assert ChatHistory.query.count() >= 1

    headers = _register_and_get_headers(client, "acct_tester", "acct_tester@example.com")
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["user"]["virtual_cash_balance"] == 100000.0


def test_ml_directions_up_down_sideways_and_save(client):
    """Scenarios 1, 2, 3, and 9: Generate UP, DOWN, SIDEWAYS predictions, save immutably, never overwrite."""
    headers = _register_and_get_headers(client, "ml_tester", "ml_tester@example.com")

    up_forecast = run_ml_prediction_from_df(_build_synthetic_ohlcv("UP"), tolerance_pct=0.50)
    down_forecast = run_ml_prediction_from_df(_build_synthetic_ohlcv("DOWN"), tolerance_pct=0.50)
    sideways_forecast = run_ml_prediction_from_df(_build_synthetic_ohlcv("SIDEWAYS"), tolerance_pct=0.50)

    assert up_forecast["predicted_direction"] == "UP"
    assert down_forecast["predicted_direction"] == "DOWN"
    assert sideways_forecast["predicted_direction"] == "SIDEWAYS"

    # Persist multiple predictions via REST API on SIMULATED_TEST feed and confirm non-overwrite
    r1 = client.post(
        "/api/predictions",
        json={"stock_symbol": "AAPL", "data_source": "SIMULATED_TEST", "horizon_days": 1},
        headers=headers,
    )
    r2 = client.post(
        "/api/predictions",
        json={"stock_symbol": "AAPL", "data_source": "SIMULATED_TEST", "horizon_days": 2},
        headers=headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    p1 = r1.get_json()["prediction"]
    p2 = r2.get_json()["prediction"]
    assert p1["prediction_id"] != p2["prediction_id"]
    assert p1["verification_status"] == "PENDING VERIFICATION"
    assert len(p1["historical_patterns"]) >= 3
    assert len(p1["invalidation_factors"]) >= 3
    assert "statistical estimate" in p1["confidence_meaning"].lower()

    # Confirm both historical records exist via GET /api/predictions/{id} and GET /api/predictions/history
    g1 = client.get(f"/api/predictions/{p1['prediction_id']}", headers=headers)
    g2 = client.get(f"/api/predictions/{p2['prediction_id']}", headers=headers)
    assert g1.status_code == 200
    assert g2.status_code == 200

    hist = client.get("/api/predictions/history?search=AAPL", headers=headers).get_json()["history"]
    ids = {row["prediction_id"] for row in hist}
    assert p1["prediction_id"] in ids and p2["prediction_id"] in ids


def test_verification_correct_incorrect_pending_and_accuracy_math(client):
    """Scenarios 4, 5, 6, 7, 8: Verify after target time, CORRECT/INCORRECT, PENDING when unavailable, MAE & Accuracy excluding pending."""
    headers = _register_and_get_headers(client, "verify_tester", "verify_tester@example.com")

    with client.application.app_context():
        # Clear predictions from earlier test inside isolated in-memory suite to verify exact math cleanly
        PredictionResult.query.delete()
        Prediction.query.delete()
        db.session.commit()

        stock = _create_isolated_stock("VTEST", base_price=100.0)
        base_date = date(2026, 9, 10)
        # Actual bar on 2026-09-11 = 104.0 (+4.0% UP vs 100.0)
        bar_target = date(2026, 9, 11)
        # Replace/add explicit bars for exact verification math
        MarketData.query.filter_by(stock_id=stock.id, date=bar_target).delete()
        db.session.add(
            MarketData(
                stock_id=stock.id,
                date=bar_target,
                open_price=101.0,
                high_price=105.0,
                low_price=100.5,
                close_price=104.0,
                volume=1_000_000,
                is_simulated=True,
            )
        )
        db.session.commit()

        # Pred 1: UP, starting 100 -> predicted 102.0 (will be CORRECT, actual 104.0, abs error = 2.0)
        p_correct = Prediction(
            prediction_id=generate_prediction_id(datetime.combine(base_date, datetime.min.time())),
            stock_id=stock.id,
            stock_symbol="VTEST",
            stock_name="VTEST Corp",
            starting_price=100.0,
            predicted_price=102.0,
            predicted_return_pct=2.0,
            predicted_direction="UP",
            prediction_timestamp=datetime.combine(base_date, datetime.min.time()),
            target_timestamp=datetime.combine(bar_target, datetime.min.time()),
            confidence_score=72.0,
            model_name="TestModel",
            model_version="v2.1.0",
            prediction_reason="Bullish momentum",
            historical_patterns_json=serialize_json_list([]),
            confidence_meaning="Test confidence",
            invalidation_factors_json=serialize_json_list([]),
            verification_status="PENDING VERIFICATION",
            prediction_result="PENDING",
            tolerance_pct=0.50,
            data_source="SIMULATED_TEST",
            is_simulated=True,
        )
        # Pred 2: DOWN, starting 100 -> predicted 98.0 (will be INCORRECT, actual 104.0, abs error = 6.0)
        p_wrong = Prediction(
            prediction_id=generate_prediction_id(datetime.combine(base_date, datetime.min.time())),
            stock_id=stock.id,
            stock_symbol="VTEST",
            stock_name="VTEST Corp",
            starting_price=100.0,
            predicted_price=98.0,
            predicted_return_pct=-2.0,
            predicted_direction="DOWN",
            prediction_timestamp=datetime.combine(base_date, datetime.min.time()),
            target_timestamp=datetime.combine(bar_target, datetime.min.time()),
            confidence_score=65.0,
            model_name="TestModel",
            model_version="v2.1.0",
            prediction_reason="Bearish signal",
            historical_patterns_json=serialize_json_list([]),
            confidence_meaning="Test confidence",
            invalidation_factors_json=serialize_json_list([]),
            verification_status="PENDING VERIFICATION",
            prediction_result="PENDING",
            tolerance_pct=0.50,
            data_source="SIMULATED_TEST",
            is_simulated=True,
        )
        # Pred 3: Future target date with NO market data bar -> must stay PENDING VERIFICATION, actual_price None!
        future_missing_date = date(2027, 5, 1)
        p_unavailable = Prediction(
            prediction_id=generate_prediction_id(datetime.combine(base_date, datetime.min.time())),
            stock_id=stock.id,
            stock_symbol="VTEST",
            stock_name="VTEST Corp",
            starting_price=100.0,
            predicted_price=100.2,
            predicted_return_pct=0.2,
            predicted_direction="SIDEWAYS",
            prediction_timestamp=datetime.combine(base_date, datetime.min.time()),
            target_timestamp=datetime.combine(future_missing_date, datetime.min.time()),
            confidence_score=58.0,
            model_name="TestModel",
            model_version="v2.1.0",
            prediction_reason="Sideways range",
            historical_patterns_json=serialize_json_list([]),
            confidence_meaning="Test confidence",
            invalidation_factors_json=serialize_json_list([]),
            verification_status="PENDING VERIFICATION",
            prediction_result="PENDING",
            tolerance_pct=0.50,
            data_source="SIMULATED_TEST",
            is_simulated=True,
        )
        db.session.add_all([p_correct, p_wrong, p_unavailable])
        db.session.commit()

        id_c = p_correct.prediction_id
        id_w = p_wrong.prediction_id
        id_u = p_unavailable.prediction_id

        # Scenario 6: Verify when target_timestamp has arrived in clock, but NO market bar exists -> remains PENDING VERIFICATION!
        verified_flag, msg = verify_single_prediction(p_unavailable, now=datetime(2027, 5, 2, 12, 0))
        assert verified_flag is False
        assert p_unavailable.verification_status == "PENDING VERIFICATION"
        assert p_unavailable.actual_price is None

    # Scenario 4, 5, 7 via REST API POST /api/predictions/{id}/verify
    res_c = client.post(
        f"/api/predictions/{id_c}/verify",
        json={"as_of_timestamp": "2026-09-12T10:00:00"},
        headers=headers,
    )
    res_w = client.post(
        f"/api/predictions/{id_w}/verify",
        json={"as_of_timestamp": "2026-09-12T10:00:00"},
        headers=headers,
    )
    assert res_c.status_code == 200 and res_c.get_json()["verified"] is True
    assert res_w.status_code == 200 and res_w.get_json()["verified"] is True

    pc_json = res_c.get_json()["prediction"]
    pw_json = res_w.get_json()["prediction"]
    assert pc_json["prediction_result"] == "CORRECT"
    assert pc_json["actual_direction"] == "UP"
    assert pc_json["absolute_price_error"] == 2.0

    assert pw_json["prediction_result"] == "INCORRECT"
    assert pw_json["actual_direction"] == "UP"
    assert pw_json["absolute_price_error"] == 6.0

    # Scenario 8: Accuracy = 1 / 2 * 100 = 50.0% (PENDING prediction excluded!), MAE = (2.0 + 6.0) / 2 = 4.0
    acc_res = client.get("/api/predictions/accuracy", headers=headers)
    assert acc_res.status_code == 200
    summary = acc_res.get_json()["summary"]
    assert summary["total_predictions"] == 3
    assert summary["verified_predictions"] == 2
    assert summary["correct_predictions"] == 1
    assert summary["incorrect_predictions"] == 1
    assert summary["pending_predictions"] == 1
    assert summary["direction_accuracy_pct"] == 50.0
    assert summary["mean_absolute_error"] == 4.0

    # Comparison endpoint check
    comp_res = client.get("/api/predictions/comparison/VTEST", headers=headers)
    assert comp_res.status_code == 200
    comp = comp_res.get_json()
    assert comp["symbol"] == "VTEST"
    assert comp["total_predictions"] == 3
    assert comp["verified_predictions"] == 2

    # Filters on /api/predictions/history
    f_corr = client.get("/api/predictions/history?result=CORRECT", headers=headers).get_json()["history"]
    assert len(f_corr) == 1 and f_corr[0]["prediction_id"] == id_c
    f_down = client.get("/api/predictions/history?direction=DOWN", headers=headers).get_json()["history"]
    assert len(f_down) == 1 and f_down[0]["prediction_id"] == id_w


def test_virtual_trading_risk_and_chat(client):
    headers = _register_and_get_headers(client, "sim_trader", "sim_trader@example.com")

    # Virtual trade on SIMULATED_TEST feed
    buy_res = client.post(
        "/api/portfolio/trade",
        json={"symbol": "AAPL", "transaction_type": "BUY", "quantity": 5, "data_source": "SIMULATED_TEST"},
        headers=headers,
    )
    assert buy_res.status_code == 201
    assert buy_res.get_json()["portfolio"]["holdings_count"] == 1

    sell_res = client.post(
        "/api/portfolio/trade",
        json={"symbol": "AAPL", "transaction_type": "SELL", "quantity": 5, "data_source": "SIMULATED_TEST"},
        headers=headers,
    )
    assert sell_res.status_code == 201
    assert sell_res.get_json()["portfolio"]["holdings_count"] == 0

    risk_res = client.get("/api/risk/overview?symbol=AAPL", headers=headers)
    assert risk_res.status_code == 200
    assert risk_res.get_json()["selected_stock_risk"]["symbol"] == "AAPL"

    chat_res = client.post(
        "/api/chat/message",
        json={"message": "Summarize our prediction accuracy and MAE"},
        headers=headers,
    )
    assert chat_res.status_code == 201
    assert chat_res.get_json()["assistant_message"]["intent"] == "prediction_history"
