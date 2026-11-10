from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from app.models import Prediction
from app.services.accountability_service import (
    compute_accountability_dashboard,
    get_symbol_comparison,
    record_new_prediction,
    verify_all_due_predictions,
    verify_single_prediction,
)
from app.services.market_provider import MarketDataUnavailableError
from app.services.scheduler_service import get_scheduler_status
from app.utils.auth import optional_auth, token_required

prediction_bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")


def _find_prediction(identifier: str) -> Prediction | None:
    if identifier.isdigit():
        pred = Prediction.query.filter_by(id=int(identifier)).first()
        if pred:
            return pred
    return Prediction.query.filter_by(prediction_id=identifier.strip().upper()).first()


def _apply_prediction_filters(query):
    search = (request.args.get("search") or request.args.get("symbol") or "").strip().upper()
    direction = (request.args.get("direction") or "").strip().upper()
    result_filter = (request.args.get("result") or "").strip().upper()
    status_filter = (request.args.get("status") or "").strip().upper()
    date_filter = (request.args.get("date") or "").strip()
    data_source = (request.args.get("data_source") or "").strip().upper()

    if search:
        query = query.filter(Prediction.stock_symbol.contains(search))

    if direction in {"UP", "DOWN", "SIDEWAYS"}:
        query = query.filter(Prediction.predicted_direction == direction)

    if result_filter in {"CORRECT", "INCORRECT", "PENDING"}:
        query = query.filter(Prediction.prediction_result == result_filter)

    if status_filter in {"VERIFIED", "PENDING VERIFICATION"}:
        query = query.filter(Prediction.verification_status == status_filter)

    if data_source in {"REAL_MARKET", "SIMULATED_TEST"}:
        query = query.filter(Prediction.data_source == data_source)

    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            day_start = datetime.combine(target_date, datetime.min.time())
            day_end = datetime.combine(target_date, datetime.max.time())
            query = query.filter(
                Prediction.prediction_timestamp >= day_start,
                Prediction.prediction_timestamp <= day_end,
            )
        except ValueError:
            pass

    return query


@prediction_bp.post("")
@prediction_bp.post("/generate")
@token_required
def create_prediction():
    data = request.get_json(silent=True) or {}
    symbol = (data.get("stock_symbol") or data.get("symbol") or "").strip().upper()
    if not symbol or len(symbol) > 16:
        return jsonify({"error": "A valid stock_symbol is required."}), 400

    data_source = (data.get("data_source") or current_app.config.get("DEFAULT_DATA_SOURCE", "REAL_MARKET")).strip().upper()
    if data_source not in {"REAL_MARKET", "SIMULATED_TEST"}:
        return jsonify({"error": "data_source must be REAL_MARKET or SIMULATED_TEST."}), 400

    horizon_days = data.get("horizon_days", 1)
    horizon_hours = data.get("horizon_hours")
    tolerance_pct = data.get("tolerance_pct", current_app.config.get("SIDEWAYS_TOLERANCE_PCT", 0.50))

    try:
        horizon_days = int(horizon_days)
        if horizon_days < 1 or horizon_days > 14:
            return jsonify({"error": "horizon_days must be between 1 and 14."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "horizon_days must be a valid integer."}), 400

    if horizon_hours is not None:
        try:
            horizon_hours = int(horizon_hours)
            if horizon_hours < 1 or horizon_hours > 72:
                return jsonify({"error": "horizon_hours must be between 1 and 72."}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "horizon_hours must be a valid integer."}), 400

    try:
        tolerance_pct = float(tolerance_pct)
        if tolerance_pct < 0.05 or tolerance_pct > 5.0:
            return jsonify({"error": "tolerance_pct must be between 0.05 and 5.0."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "tolerance_pct must be a valid number."}), 400

    target_ts = None
    if data.get("target_timestamp"):
        try:
            target_ts = datetime.fromisoformat(str(data["target_timestamp"]).replace("Z", ""))
        except ValueError:
            return jsonify({"error": "Invalid ISO target_timestamp format."}), 400

    try:
        prediction = record_new_prediction(
            symbol=symbol,
            user_id=g.current_user.id,
            data_source=data_source,
            horizon_days=horizon_days,
            horizon_hours=horizon_hours,
            tolerance_pct=tolerance_pct,
            target_timestamp=target_ts,
        )
    except MarketDataUnavailableError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "message": f"Recorded prediction {prediction.prediction_id} ({prediction.predicted_direction}) for {prediction.stock_symbol}.",
            "prediction": prediction.to_dict(),
        }
    ), 201


@prediction_bp.get("")
@optional_auth
def list_predictions():
    limit = request.args.get("limit", default=80, type=int)
    limit = max(1, min(limit or 80, 250))

    query = Prediction.query
    if g.current_user:
        query = query.filter((Prediction.user_id == g.current_user.id) | (Prediction.user_id.is_(None)))
    else:
        query = query.filter(Prediction.user_id.is_(None))

    query = _apply_prediction_filters(query)
    items = (
        query.order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"predictions": [p.to_dict() for p in items], "total": len(items)}), 200


@prediction_bp.get("/history")
@optional_auth
def get_prediction_history():
    limit = request.args.get("limit", default=150, type=int)
    limit = max(1, min(limit or 150, 500))
    offset = max(0, request.args.get("offset", default=0, type=int) or 0)

    query = Prediction.query
    if g.current_user:
        query = query.filter((Prediction.user_id == g.current_user.id) | (Prediction.user_id.is_(None)))
    else:
        query = query.filter(Prediction.user_id.is_(None))

    query = _apply_prediction_filters(query)
    total_count = query.count()
    items = (
        query.order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "history": [p.to_dict() for p in items],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
    ), 200


@prediction_bp.get("/accuracy")
@prediction_bp.get("/reports")
@optional_auth
def get_prediction_accuracy():
    symbol = (request.args.get("symbol") or "").strip().upper() or None
    data_source = (request.args.get("data_source") or "").strip().upper() or None
    user_id = g.current_user.id if g.current_user else None

    dashboard = compute_accountability_dashboard(
        symbol=symbol,
        data_source=data_source,
        user_id=user_id,
    )
    dashboard["scheduler"] = get_scheduler_status()
    return jsonify(dashboard), 200


@prediction_bp.get("/comparison/<symbol>")
@optional_auth
def get_prediction_comparison(symbol: str):
    data_source = (request.args.get("data_source") or "").strip().upper() or None
    user_id = g.current_user.id if g.current_user else None
    comparison = get_symbol_comparison(
        symbol=symbol,
        user_id=user_id,
        data_source=data_source,
    )
    return jsonify(comparison), 200


@prediction_bp.get("/scheduler-status")
def scheduler_status():
    return jsonify(get_scheduler_status()), 200


@prediction_bp.post("/verify-due")
@prediction_bp.post("/evaluate")
@token_required
def verify_due():
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or "").strip().upper() or None
    data_source = (data.get("data_source") or "").strip().upper() or None
    summary = verify_all_due_predictions(symbol=symbol, data_source=data_source)
    return jsonify(
        {
            "message": f"Checked {summary['checked_count']} due prediction(s): {summary['verified_count']} verified, {summary['pending_count']} still pending verification.",
            **summary,
        }
    ), 200


@prediction_bp.get("/<pred_identifier>")
@optional_auth
def get_prediction_detail(pred_identifier: str):
    pred = _find_prediction(pred_identifier)
    if not pred:
        return jsonify({"error": f"Prediction '{pred_identifier}' not found."}), 404
    return jsonify({"prediction": pred.to_dict()}), 200


@prediction_bp.post("/<pred_identifier>/verify")
@token_required
def verify_prediction_by_id(pred_identifier: str):
    pred = _find_prediction(pred_identifier)
    if not pred:
        return jsonify({"error": f"Prediction '{pred_identifier}' not found."}), 404

    data = request.get_json(silent=True) or {}
    now_override = None
    if data.get("as_of_timestamp"):
        try:
            now_override = datetime.fromisoformat(str(data["as_of_timestamp"]).replace("Z", ""))
        except ValueError:
            return jsonify({"error": "Invalid as_of_timestamp ISO format."}), 400

    verified, msg = verify_single_prediction(pred, now=now_override or datetime.now(timezone.utc).replace(tzinfo=None))
    return jsonify(
        {
            "verified": verified,
            "message": msg,
            "prediction": pred.to_dict(),
        }
    ), 200
