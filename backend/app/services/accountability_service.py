from collections import defaultdict
from datetime import datetime, timezone
import uuid

from app.extensions import db
from app.models import Prediction, PredictionResult, Stock
from app.services.market_provider import (
    MarketDataUnavailableError,
    fetch_actual_price_for_target,
    get_market_series,
)
from app.services.ml_engine import generate_live_prediction, serialize_json_list


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_prediction_id(pred_ts: datetime) -> str:
    date_part = pred_ts.strftime("%Y%m%d")
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"PRED-{date_part}-{short_uid}"


def record_new_prediction(
    symbol: str,
    user_id: int | None = None,
    data_source: str = "REAL_MARKET",
    horizon_days: int = 1,
    horizon_hours: int | None = None,
    tolerance_pct: float = 0.50,
    target_timestamp: datetime | None = None,
) -> Prediction:
    """
    Runs the Scikit-learn prediction pipeline and permanently appends a new Prediction row.
    Never overwrites existing predictions.
    """
    clean_symbol = symbol.strip().upper()
    stock_meta, forecast = generate_live_prediction(
        symbol=clean_symbol,
        data_source=data_source,
        horizon_days=horizon_days,
        horizon_hours=horizon_hours,
        tolerance_pct=tolerance_pct,
        target_timestamp=target_timestamp,
    )

    local_stock = Stock.query.filter_by(symbol=clean_symbol).first()
    pred_ts = forecast["prediction_timestamp"]

    prediction = Prediction(
        prediction_id=generate_prediction_id(pred_ts),
        user_id=user_id,
        stock_id=local_stock.id if local_stock else None,
        stock_symbol=clean_symbol,
        stock_name=stock_meta.get("name", clean_symbol),
        starting_price=forecast["starting_price"],
        predicted_price=forecast["predicted_price"],
        predicted_return_pct=forecast["predicted_return_pct"],
        predicted_direction=forecast["predicted_direction"],
        prediction_timestamp=pred_ts,
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
        data_source=stock_meta.get("data_source", data_source),
        is_simulated=bool(stock_meta.get("is_simulated", data_source == "SIMULATED_TEST")),
    )
    db.session.add(prediction)
    db.session.commit()
    db.session.refresh(prediction)
    return prediction


def verify_single_prediction(prediction: Prediction, now: datetime | None = None) -> tuple[bool, str]:
    """
    Verifies a prediction against actual market data after target_timestamp is reached.
    If market data is unavailable, keeps status as PENDING VERIFICATION and never invents prices.
    """
    current_time = now or _utcnow()

    if prediction.verification_status == "VERIFIED":
        return False, f"Prediction {prediction.prediction_id} is already VERIFIED."

    if current_time < prediction.target_timestamp:
        return (
            False,
            f"Target time ({prediction.target_timestamp.isoformat()}) has not been reached yet; status remains PENDING VERIFICATION.",
        )

    try:
        actual_price, actual_bar_ts = fetch_actual_price_for_target(
            symbol=prediction.stock_symbol,
            target_timestamp=prediction.target_timestamp,
            data_source=prediction.data_source,
        )
    except MarketDataUnavailableError as exc:
        prediction.verification_status = "PENDING VERIFICATION"
        prediction.prediction_result = "PENDING"
        prediction.verification_notes = (
            f"Last checked at {current_time.isoformat()}: {exc} Status kept as PENDING VERIFICATION."
        )
        db.session.commit()
        return False, str(exc)

    base_price = float(prediction.starting_price)
    actual_return_pct = ((actual_price - base_price) / base_price) * 100.0 if base_price > 0 else 0.0
    tol = float(prediction.tolerance_pct)

    if actual_return_pct > tol:
        actual_direction = "UP"
    elif actual_return_pct < -tol:
        actual_direction = "DOWN"
    else:
        actual_direction = "SIDEWAYS"

    is_correct = prediction.predicted_direction == actual_direction
    prediction_result = "CORRECT" if is_correct else "INCORRECT"

    abs_error = abs(actual_price - float(prediction.predicted_price))
    err_pct = (abs_error / actual_price) * 100.0 if actual_price > 0 else 0.0

    notes = (
        f"[{prediction_result}] Predicted {prediction.predicted_direction} (${prediction.predicted_price:.2f}) vs "
        f"Actual {actual_direction} (${actual_price:.2f}, {actual_return_pct:+.2f}%) at bar {actual_bar_ts.isoformat()}. "
        f"Tolerance: +/-{tol:.2f}%. Absolute error: ${abs_error:.2f} ({err_pct:.2f}%)."
    )

    prediction.actual_price = round(actual_price, 2)
    prediction.actual_return_pct = round(actual_return_pct, 2)
    prediction.actual_direction = actual_direction
    prediction.absolute_price_error = round(abs_error, 2)
    prediction.price_error_pct = round(err_pct, 2)
    prediction.verification_status = "VERIFIED"
    prediction.prediction_result = prediction_result
    prediction.verification_timestamp = current_time
    prediction.verification_notes = notes

    if prediction.result_record is None:
        db.session.add(
            PredictionResult(
                prediction_id=prediction.id,
                actual_price=round(actual_price, 2),
                actual_return_pct=round(actual_return_pct, 2),
                actual_direction=actual_direction,
                price_error=round(abs_error, 2),
                price_error_pct=round(err_pct, 2),
                is_correct=is_correct,
                evaluation_notes=notes,
                evaluated_at=current_time,
            )
        )

    db.session.commit()
    return True, notes


def verify_all_due_predictions(
    symbol: str | None = None,
    data_source: str | None = None,
    now: datetime | None = None,
) -> dict:
    current_time = now or _utcnow()
    query = Prediction.query.filter(
        Prediction.verification_status == "PENDING VERIFICATION",
        Prediction.target_timestamp <= current_time,
    )
    if symbol:
        query = query.filter(Prediction.stock_symbol == symbol.strip().upper())
    if data_source:
        query = query.filter(Prediction.data_source == data_source.strip().upper())

    due = query.order_by(Prediction.target_timestamp.asc()).all()
    verified_count = 0
    still_pending_count = 0
    details = []

    for pred in due:
        ok, msg = verify_single_prediction(pred, now=current_time)
        if ok:
            verified_count += 1
        else:
            still_pending_count += 1
        details.append({"prediction_id": pred.prediction_id, "verified": ok, "message": msg})

    return {
        "checked_count": len(due),
        "verified_count": verified_count,
        "pending_count": still_pending_count,
        "details": details,
        "checked_at": current_time.isoformat(),
    }


def _aggregate_periods(verified_preds: list[Prediction], period_fn) -> list[dict]:
    buckets = defaultdict(list)
    for p in verified_preds:
        buckets[period_fn(p.target_timestamp)].append(p)

    reports = []
    for key in sorted(buckets.keys()):
        items = buckets[key]
        total = len(items)
        correct = sum(1 for p in items if p.prediction_result == "CORRECT")
        incorrect = total - correct
        acc = round((correct / total) * 100.0, 1) if total else 0.0
        mae = round(sum(p.absolute_price_error or 0.0 for p in items) / total, 2) if total else 0.0
        mape = round(sum(p.price_error_pct or 0.0 for p in items) / total, 2) if total else 0.0

        by_sym = defaultdict(lambda: [0, 0])
        for p in items:
            by_sym[p.stock_symbol][0] += 1
            if p.prediction_result == "CORRECT":
                by_sym[p.stock_symbol][1] += 1
        best_sym = max(by_sym.items(), key=lambda kv: (kv[1][1] / kv[1][0], kv[1][0]))[0]

        reports.append(
            {
                "period": key,
                "verified_predictions": total,
                "correct": correct,
                "incorrect": incorrect,
                "accuracy_pct": acc,
                "mae": mae,
                "mape_pct": mape,
                "top_performing_symbol": best_sym,
            }
        )
    return reports


def compute_accountability_dashboard(
    symbol: str | None = None,
    data_source: str | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Computes complete Prediction Accountability Dashboard metrics.
    Strictly excludes PENDING VERIFICATION predictions from accuracy & MAE calculations.
    """
    query = Prediction.query
    if user_id is not None:
        query = query.filter((Prediction.user_id == user_id) | (Prediction.user_id.is_(None)))
    if symbol:
        query = query.filter(Prediction.stock_symbol == symbol.strip().upper())
    if data_source:
        query = query.filter(Prediction.data_source == data_source.strip().upper())

    all_preds = query.order_by(Prediction.prediction_timestamp.asc(), Prediction.id.asc()).all()

    total_predictions = len(all_preds)
    verified = [p for p in all_preds if p.verification_status == "VERIFIED"]
    pending = [p for p in all_preds if p.verification_status != "VERIFIED"]

    verified_count = len(verified)
    pending_count = len(pending)
    correct_count = sum(1 for p in verified if p.prediction_result == "CORRECT")
    incorrect_count = verified_count - correct_count

    direction_accuracy_pct = round((correct_count / verified_count) * 100.0, 1) if verified_count > 0 else 0.0
    mae = round(sum(p.absolute_price_error or 0.0 for p in verified) / verified_count, 2) if verified_count > 0 else 0.0
    mape_pct = round(sum(p.price_error_pct or 0.0 for p in verified) / verified_count, 2) if verified_count > 0 else 0.0
    avg_confidence = round(sum(p.confidence_score for p in verified) / verified_count, 1) if verified_count > 0 else 0.0

    # Transparent Prediction Accountability Score (0 - 100)
    if verified_count > 0:
        precision_score = max(0.0, 100.0 - (mape_pct * 10.0))
        calibration_score = max(0.0, 100.0 - abs(avg_confidence - direction_accuracy_pct))
        accountability_score = round(
            (0.60 * direction_accuracy_pct) + (0.25 * precision_score) + (0.15 * calibration_score),
            1,
        )
    else:
        precision_score = 0.0
        calibration_score = 0.0
        accountability_score = 0.0

    direction_breakdown = {}
    for direction in ("UP", "DOWN", "SIDEWAYS"):
        items = [p for p in verified if p.predicted_direction == direction]
        c = sum(1 for p in items if p.prediction_result == "CORRECT")
        direction_breakdown[direction] = {
            "verified": len(items),
            "correct": c,
            "incorrect": len(items) - c,
            "accuracy_pct": round((c / len(items)) * 100.0, 1) if items else 0.0,
        }

    # Stock-wise accuracy + best & weak stocks
    by_stock = defaultdict(list)
    for p in verified:
        by_stock[p.stock_symbol].append(p)

    stock_wise_accuracy = []
    for sym, items in sorted(by_stock.items()):
        v = len(items)
        c = sum(1 for p in items if p.prediction_result == "CORRECT")
        s_mae = sum(p.absolute_price_error or 0.0 for p in items) / v
        s_mape = sum(p.price_error_pct or 0.0 for p in items) / v
        stock_wise_accuracy.append(
            {
                "symbol": sym,
                "stock_name": items[0].stock_name,
                "verified_predictions": v,
                "correct": c,
                "incorrect": v - c,
                "accuracy_pct": round((c / v) * 100.0, 1),
                "mae": round(s_mae, 2),
                "mape_pct": round(s_mape, 2),
            }
        )

    ranked_best = sorted(stock_wise_accuracy, key=lambda r: (-r["accuracy_pct"], r["mae"]))
    ranked_weak = sorted(stock_wise_accuracy, key=lambda r: (r["accuracy_pct"], -r["mae"]))

    weekly_accuracy = _aggregate_periods(
        verified,
        lambda dt: f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}",
    )
    monthly_accuracy = _aggregate_periods(
        verified,
        lambda dt: dt.strftime("%Y-%m"),
    )

    daily_buckets = defaultdict(list)
    for p in verified:
        daily_buckets[p.target_timestamp.date().isoformat()].append(p)

    performance_over_time = []
    running_v = 0
    running_c = 0
    for d_str in sorted(daily_buckets.keys()):
        day_items = daily_buckets[d_str]
        dv = len(day_items)
        dc = sum(1 for p in day_items if p.prediction_result == "CORRECT")
        running_v += dv
        running_c += dc
        day_mae = round(sum(p.absolute_price_error or 0.0 for p in day_items) / dv, 2)
        performance_over_time.append(
            {
                "date": d_str,
                "daily_accuracy_pct": round((dc / dv) * 100.0, 1),
                "cumulative_accuracy_pct": round((running_c / running_v) * 100.0, 1),
                "verified_count": dv,
                "correct_count": dc,
                "mae": day_mae,
            }
        )

    return {
        "summary": {
            "total_predictions": total_predictions,
            "verified_predictions": verified_count,
            "correct_predictions": correct_count,
            "incorrect_predictions": incorrect_count,
            "pending_predictions": pending_count,
            "direction_accuracy_pct": direction_accuracy_pct,
            "accuracy_pct": direction_accuracy_pct,
            "mean_absolute_error": mae,
            "mean_absolute_pct_error": mape_pct,
            "avg_confidence_score": avg_confidence,
            "accountability_score": accountability_score,
            "pending_excluded_note": "Pending verification predictions are strictly excluded from direction accuracy and MAE calculations.",
        },
        "accountability_score_details": {
            "score": accountability_score,
            "formula": "60% × Direction Accuracy + 25% × Price Precision (100 - 10×MAPE) + 15% × Confidence Calibration (100 - |Avg Confidence - Accuracy|)",
            "components": {
                "direction_accuracy_pct": direction_accuracy_pct,
                "direction_weight": "60%",
                "price_precision_score": round(precision_score, 1),
                "price_precision_weight": "25%",
                "confidence_calibration_score": round(calibration_score, 1),
                "confidence_calibration_weight": "15%",
            },
            "disclaimer": "Past Prediction Accountability Scores reflect historical verified outcomes only and never guarantee future prediction accuracy or financial returns.",
        },
        "direction_breakdown": direction_breakdown,
        "stock_wise_accuracy": ranked_best,
        "best_performing_stocks": ranked_best[:3],
        "weak_performing_stocks": ranked_weak[:3],
        "weekly_accuracy": weekly_accuracy,
        "monthly_accuracy": monthly_accuracy,
        "performance_over_time": performance_over_time,
    }


def get_symbol_comparison(
    symbol: str,
    user_id: int | None = None,
    data_source: str | None = None,
) -> dict:
    clean_symbol = symbol.strip().upper()
    query = Prediction.query.filter(Prediction.stock_symbol == clean_symbol)
    if user_id is not None:
        query = query.filter((Prediction.user_id == user_id) | (Prediction.user_id.is_(None)))
    if data_source:
        query = query.filter(Prediction.data_source == data_source.strip().upper())

    items = query.order_by(Prediction.prediction_timestamp.asc(), Prediction.id.asc()).all()
    serialized = [p.to_dict() for p in items]

    verified_items = [p for p in items if p.verification_status == "VERIFIED"]
    correct_count = sum(1 for p in verified_items if p.prediction_result == "CORRECT")
    acc = round((correct_count / len(verified_items)) * 100.0, 1) if verified_items else 0.0
    mae = round(sum(p.absolute_price_error or 0.0 for p in verified_items) / len(verified_items), 2) if verified_items else 0.0

    # Also fetch market trend context for visual reference if available
    market_curve = []
    preferred_source = (items[-1].data_source if items else data_source) or "SIMULATED_TEST"
    try:
        _, df = get_market_series(clean_symbol, data_source=preferred_source)
        for row in df.tail(45).itertuples():
            market_curve.append({"date": row.date.isoformat(), "close": round(float(row.close), 2)})
    except MarketDataUnavailableError:
        market_curve = []

    return {
        "symbol": clean_symbol,
        "total_predictions": len(serialized),
        "verified_predictions": len(verified_items),
        "correct_predictions": correct_count,
        "direction_accuracy_pct": acc,
        "mean_absolute_error": mae,
        "predictions": serialized,
        "market_curve": market_curve,
    }
