from flask import Blueprint, g, jsonify, request

from app.services.risk_service import build_risk_overview
from app.utils.auth import optional_auth

risk_bp = Blueprint("risk", __name__, url_prefix="/api/risk")


@risk_bp.get("/overview")
@optional_auth
def risk_overview():
    symbol = (request.args.get("symbol") or "").strip().upper() or None
    overview = build_risk_overview(user=g.current_user, focus_symbol=symbol)
    return jsonify(overview), 200

