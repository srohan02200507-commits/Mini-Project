from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models import User
from app.utils.auth import generate_auth_token, token_required
from app.utils.validators import validate_registration_payload

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_registration_payload(data)
    if errors:
        return jsonify({"error": errors[0], "errors": errors}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    full_name = data["full_name"].strip()
    experience_level = (data.get("experience_level") or "beginner").strip().lower()

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "An account with this username or email already exists."}), 409

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        experience_level=experience_level,
        virtual_cash_balance=100000.0,
        initial_cash_balance=100000.0,
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    token = generate_auth_token(user)
    return jsonify(
        {
            "message": "Account created successfully with $100,000.00 in virtual practice funds.",
            "token": token,
            "user": user.to_dict(),
        }
    ), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials. Please check your username/email and password."}), 401

    token = generate_auth_token(user)
    return jsonify(
        {
            "message": "Signed in successfully.",
            "token": token,
            "user": user.to_dict(),
        }
    ), 200


@auth_bp.post("/logout")
@token_required
def logout():
    return jsonify({"message": "Signed out successfully."}), 200


@auth_bp.get("/me")
@token_required
def get_me():
    return jsonify({"user": g.current_user.to_dict()}), 200

