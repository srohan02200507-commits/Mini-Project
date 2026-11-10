from functools import wraps
from datetime import datetime, timezone

import jwt
from flask import current_app, g, jsonify, request

from app.extensions import db
from app.models import User


def generate_auth_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "iat": int(now.timestamp()),
        "exp": int((now + current_app.config["JWT_EXPIRATION"]).timestamp()),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_auth_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "Authentication token is required."}), 401

        payload = decode_auth_token(token)
        if not payload or "sub" not in payload:
            return jsonify({"error": "Invalid or expired authentication token."}), 401

        try:
            user_id = int(payload["sub"])
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid authentication token subject."}), 401

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User account no longer exists."}), 401

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def optional_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = None
        token = _extract_bearer_token()
        if token:
            payload = decode_auth_token(token)
            if payload and "sub" in payload:
                try:
                    g.current_user = db.session.get(User, int(payload["sub"]))
                except (TypeError, ValueError):
                    g.current_user = None
        return fn(*args, **kwargs)

    return wrapper
