from flask import Blueprint, g, jsonify, request

from app.models import Transaction
from app.services.market_provider import MarketDataUnavailableError
from app.services.trading_service import (
    execute_virtual_trade,
    get_portfolio_summary,
    reset_virtual_account,
)
from app.utils.auth import token_required
from app.utils.validators import validate_trade_payload

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/api/portfolio")


@portfolio_bp.get("")
@token_required
def get_portfolio():
    refresh_live = request.args.get("live", default="false").lower() == "true"
    summary = get_portfolio_summary(g.current_user, refresh_live=refresh_live)
    return jsonify(summary), 200


@portfolio_bp.get("/transactions")
@token_required
def list_transactions():
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit or 50, 200))

    items = (
        Transaction.query.filter_by(user_id=g.current_user.id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify(
        {
            "transactions": [t.to_dict() for t in items],
            "total": len(items),
            "is_simulated": True,
        }
    ), 200


@portfolio_bp.post("/trade")
@token_required
def place_virtual_trade():
    data = request.get_json(silent=True) or {}
    side = (data.get("transaction_type") or data.get("side") or "").strip().upper()
    if side not in {"BUY", "SELL"}:
        return jsonify({"error": "Transaction type must be BUY or SELL."}), 400

    data_source = (data.get("data_source") or "REAL_MARKET").strip().upper()
    if data_source not in {"REAL_MARKET", "SIMULATED_TEST"}:
        return jsonify({"error": "data_source must be REAL_MARKET or SIMULATED_TEST."}), 400

    errors, symbol, quantity = validate_trade_payload(data)
    if errors:
        return jsonify({"error": errors[0], "errors": errors}), 400

    notes = (data.get("notes") or "").strip()[:240] or None

    try:
        tx, _ = execute_virtual_trade(
            user=g.current_user,
            symbol=symbol,
            side=side,
            quantity=quantity,
            data_source=data_source,
            notes=notes,
        )
    except MarketDataUnavailableError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    summary = get_portfolio_summary(g.current_user, refresh_live=(data_source == "REAL_MARKET"))
    return jsonify(
        {
            "message": f"[{data_source}] Virtual {side} order filled for {quantity:g} {symbol} @ ${tx.price_per_share:.2f}.",
            "transaction": tx.to_dict(),
            "portfolio": summary,
        }
    ), 201


@portfolio_bp.post("/reset")
@token_required
def reset_portfolio():
    summary = reset_virtual_account(g.current_user)
    return jsonify(
        {
            "message": "Virtual portfolio has been reset to $100,000.00 in virtual cash.",
            "portfolio": summary,
        }
    ), 200
