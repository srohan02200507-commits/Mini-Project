from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models import ChatHistory
from app.services.chat_service import process_chat_message
from app.utils.auth import token_required

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.get("/history")
@token_required
def get_chat_history():
    limit = request.args.get("limit", default=60, type=int)
    limit = max(1, min(limit or 60, 200))

    messages = (
        ChatHistory.query.filter_by(user_id=g.current_user.id)
        .order_by(ChatHistory.created_at.asc(), ChatHistory.id.asc())
        .limit(limit)
        .all()
    )
    return jsonify({"messages": [m.to_dict() for m in messages]}), 200


@chat_bp.post("/message")
@token_required
def post_chat_message():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    context_symbol = (data.get("context_symbol") or "").strip().upper() or None

    if not message:
        return jsonify({"error": "Message text cannot be empty."}), 400
    if len(message) > 1500:
        return jsonify({"error": "Message exceeds maximum length of 1,500 characters."}), 400

    user_msg, assistant_msg = process_chat_message(
        user=g.current_user,
        message=message,
        context_symbol=context_symbol,
    )
    return jsonify(
        {
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
        }
    ), 201


@chat_bp.delete("/history")
@token_required
def clear_chat_history():
    ChatHistory.query.filter_by(user_id=g.current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "Chat history cleared."}), 200

