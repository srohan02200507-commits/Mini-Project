import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def validate_registration_payload(data: dict) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["Request body must be a valid JSON object."]

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    if not USERNAME_REGEX.match(username):
        errors.append("Username must be 3-32 characters using letters, numbers, or underscores.")
    if not EMAIL_REGEX.match(email):
        errors.append("Please provide a valid email address.")
    if len(password) < 6:
        errors.append("Password must be at least 6 characters long.")
    if len(full_name) < 2:
        errors.append("Full name must be at least 2 characters long.")

    experience = (data.get("experience_level") or "beginner").strip().lower()
    if experience not in {"beginner", "intermediate", "advanced"}:
        errors.append("Experience level must be beginner, intermediate, or advanced.")

    return errors


def validate_trade_payload(data: dict) -> tuple[list[str], str, float]:
    errors = []
    if not isinstance(data, dict):
        return ["Request body must be a valid JSON object."], "", 0.0

    symbol = (data.get("symbol") or "").strip().upper()
    if not symbol or len(symbol) > 16:
        errors.append("A valid stock symbol is required.")

    raw_qty = data.get("quantity")
    try:
        quantity = float(raw_qty)
    except (TypeError, ValueError):
        return errors + ["Quantity must be a positive number."], symbol, 0.0

    if quantity <= 0:
        errors.append("Quantity must be greater than zero.")
    elif quantity > 100000:
        errors.append("Quantity exceeds single-order simulation limit of 100,000 shares.")

    return errors, symbol, round(quantity, 4)

