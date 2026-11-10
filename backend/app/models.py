import json
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    experience_level = db.Column(db.String(32), default="beginner", nullable=False)
    virtual_cash_balance = db.Column(db.Float, default=100000.0, nullable=False)
    initial_cash_balance = db.Column(db.Float, default=100000.0, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    portfolios = db.relationship("VirtualPortfolio", back_populates="user", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    predictions = db.relationship("Prediction", back_populates="user")
    chat_messages = db.relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "experience_level": self.experience_level,
            "virtual_cash_balance": round(self.virtual_cash_balance, 2),
            "initial_cash_balance": round(self.initial_cash_balance, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Stock(db.Model):
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(64), nullable=False)
    market_cap_tier = db.Column(db.String(32), nullable=False)
    description = db.Column(db.Text, nullable=False)
    base_volatility = db.Column(db.Float, nullable=False)
    drift_bias = db.Column(db.Float, default=0.08, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    previous_close = db.Column(db.Float, nullable=False)
    day_change_pct = db.Column(db.Float, default=0.0, nullable=False)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    last_updated_date = db.Column(db.Date, nullable=False)

    market_data = db.relationship("MarketData", back_populates="stock", cascade="all, delete-orphan")
    predictions = db.relationship("Prediction", back_populates="stock")
    portfolio_items = db.relationship("VirtualPortfolio", back_populates="stock", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="stock", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "market_cap_tier": self.market_cap_tier,
            "description": self.description,
            "base_volatility": round(self.base_volatility, 4),
            "current_price": round(self.current_price, 2),
            "previous_close": round(self.previous_close, 2),
            "day_change_pct": round(self.day_change_pct, 2),
            "is_simulated": self.is_simulated,
            "data_source": "SIMULATED_TEST" if self.is_simulated else "REAL_MARKET",
            "last_updated_date": self.last_updated_date.isoformat() if self.last_updated_date else None,
        }


class MarketData(db.Model):
    __tablename__ = "market_data"
    __table_args__ = (db.UniqueConstraint("stock_id", "date", name="uq_stock_date"),)

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)

    stock = db.relationship("Stock", back_populates="market_data")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_id": self.stock_id,
            "date": self.date.isoformat(),
            "open": round(self.open_price, 2),
            "high": round(self.high_price, 2),
            "low": round(self.low_price, 2),
            "close": round(self.close_price, 2),
            "volume": self.volume,
            "is_simulated": self.is_simulated,
        }


class Prediction(db.Model):
    """Immutable Prediction Accountability Ledger record (never overwrite past predictions)."""

    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=True, index=True)

    stock_symbol = db.Column(db.String(16), nullable=False, index=True)
    stock_name = db.Column(db.String(120), nullable=False)

    starting_price = db.Column(db.Float, nullable=False)
    predicted_price = db.Column(db.Float, nullable=False)
    predicted_return_pct = db.Column(db.Float, nullable=False)
    predicted_direction = db.Column(db.String(16), nullable=False, index=True)  # UP, DOWN, SIDEWAYS

    actual_price = db.Column(db.Float, nullable=True)
    actual_return_pct = db.Column(db.Float, nullable=True)
    actual_direction = db.Column(db.String(16), nullable=True)  # UP, DOWN, SIDEWAYS

    prediction_timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    target_timestamp = db.Column(db.DateTime, nullable=False, index=True)
    verification_timestamp = db.Column(db.DateTime, nullable=True)

    confidence_score = db.Column(db.Float, nullable=False)
    model_name = db.Column(db.String(80), nullable=False)
    model_version = db.Column(db.String(32), nullable=False)
    horizon_label = db.Column(db.String(24), default="1D", nullable=False)

    prediction_reason = db.Column(db.Text, nullable=False)
    historical_patterns_json = db.Column(db.Text, nullable=False)
    confidence_meaning = db.Column(db.Text, nullable=False)
    invalidation_factors_json = db.Column(db.Text, nullable=False)

    verification_status = db.Column(
        db.String(32),
        default="PENDING VERIFICATION",
        nullable=False,
        index=True,
    )
    prediction_result = db.Column(
        db.String(24),
        default="PENDING",
        nullable=False,
        index=True,
    )
    absolute_price_error = db.Column(db.Float, nullable=True)
    price_error_pct = db.Column(db.Float, nullable=True)
    tolerance_pct = db.Column(db.Float, default=0.5, nullable=False)

    data_source = db.Column(db.String(24), default="SIMULATED_TEST", nullable=False)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    verification_notes = db.Column(db.Text, nullable=True)

    stock = db.relationship("Stock", back_populates="predictions")
    user = db.relationship("User", back_populates="predictions")
    result_record = db.relationship(
        "PredictionResult",
        back_populates="prediction",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @staticmethod
    def _safe_json(raw: str) -> list:
        try:
            parsed = json.loads(raw or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def to_dict(self) -> dict:
        price_diff = (
            round(self.actual_price - self.predicted_price, 2)
            if self.actual_price is not None
            else None
        )
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "user_id": self.user_id,
            "stock_id": self.stock_id,
            "stock_symbol": self.stock_symbol,
            "symbol": self.stock_symbol,
            "stock_name": self.stock_name,
            "starting_price": round(self.starting_price, 2),
            "predicted_price": round(self.predicted_price, 2),
            "predicted_return_pct": round(self.predicted_return_pct, 2),
            "predicted_direction": self.predicted_direction,
            "actual_price": round(self.actual_price, 2) if self.actual_price is not None else None,
            "actual_return_pct": round(self.actual_return_pct, 2) if self.actual_return_pct is not None else None,
            "actual_direction": self.actual_direction,
            "price_difference": price_diff,
            "prediction_timestamp": self.prediction_timestamp.isoformat() if self.prediction_timestamp else None,
            "target_timestamp": self.target_timestamp.isoformat() if self.target_timestamp else None,
            "verification_timestamp": self.verification_timestamp.isoformat() if self.verification_timestamp else None,
            "prediction_date": self.prediction_timestamp.date().isoformat() if self.prediction_timestamp else None,
            "target_date": self.target_timestamp.date().isoformat() if self.target_timestamp else None,
            "confidence_score": round(self.confidence_score, 1),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "horizon_label": self.horizon_label,
            "prediction_reason": self.prediction_reason,
            "historical_patterns": self._safe_json(self.historical_patterns_json),
            "confidence_meaning": self.confidence_meaning,
            "invalidation_factors": self._safe_json(self.invalidation_factors_json),
            "verification_status": self.verification_status,
            "prediction_result": self.prediction_result,
            "absolute_price_error": round(self.absolute_price_error, 2) if self.absolute_price_error is not None else None,
            "price_error_pct": round(self.price_error_pct, 2) if self.price_error_pct is not None else None,
            "tolerance_pct": round(self.tolerance_pct, 2),
            "data_source": self.data_source,
            "is_simulated": self.is_simulated,
            "verification_notes": self.verification_notes,
        }


class PredictionResult(db.Model):
    __tablename__ = "prediction_results"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), unique=True, nullable=False)
    actual_price = db.Column(db.Float, nullable=False)
    actual_return_pct = db.Column(db.Float, nullable=False)
    actual_direction = db.Column(db.String(16), nullable=False)
    price_error = db.Column(db.Float, nullable=False)
    price_error_pct = db.Column(db.Float, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    evaluation_notes = db.Column(db.Text, nullable=False)
    evaluated_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    prediction = db.relationship("Prediction", back_populates="result_record")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "actual_price": round(self.actual_price, 2),
            "actual_return_pct": round(self.actual_return_pct, 2),
            "actual_direction": self.actual_direction,
            "price_error": round(self.price_error, 2),
            "price_error_pct": round(self.price_error_pct, 2),
            "is_correct": self.is_correct,
            "evaluation_notes": self.evaluation_notes,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


class VirtualPortfolio(db.Model):
    __tablename__ = "virtual_portfolios"
    __table_args__ = (db.UniqueConstraint("user_id", "stock_symbol", "data_source", name="uq_user_symbol_source"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=True, index=True)
    stock_symbol = db.Column(db.String(16), nullable=False, index=True)
    stock_name = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(64), default="Equities", nullable=False)
    data_source = db.Column(db.String(24), default="REAL_MARKET", nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=False)
    last_known_price = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="portfolios")
    stock = db.relationship("Stock", back_populates="portfolio_items")

    def to_dict(self, live_price: float | None = None) -> dict:
        current_price = float(
            live_price
            if live_price is not None
            else (self.stock.current_price if self.data_source == "SIMULATED_TEST" and self.stock else self.last_known_price)
        )
        market_value = self.quantity * current_price
        cost_basis = self.quantity * self.average_buy_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        return {
            "id": self.id,
            "user_id": self.user_id,
            "stock_id": self.stock_id,
            "symbol": self.stock_symbol,
            "name": self.stock_name,
            "sector": self.sector,
            "data_source": self.data_source,
            "is_simulated": self.data_source == "SIMULATED_TEST",
            "quantity": round(self.quantity, 4),
            "average_buy_price": round(self.average_buy_price, 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "cost_basis": round(cost_basis, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stocks.id"), nullable=True, index=True)
    stock_symbol = db.Column(db.String(16), nullable=False, index=True)
    stock_name = db.Column(db.String(120), nullable=False)
    data_source = db.Column(db.String(24), default="REAL_MARKET", nullable=False)
    transaction_type = db.Column(db.String(16), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price_per_share = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    realized_pnl = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(256), nullable=True)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="transactions")
    stock = db.relationship("Stock", back_populates="transactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stock_id": self.stock_id,
            "symbol": self.stock_symbol,
            "stock_name": self.stock_name,
            "data_source": self.data_source,
            "transaction_type": self.transaction_type,
            "quantity": round(self.quantity, 4),
            "price_per_share": round(self.price_per_share, 2),
            "total_amount": round(self.total_amount, 2),
            "realized_pnl": round(self.realized_pnl, 2) if self.realized_pnl is not None else None,
            "notes": self.notes,
            "is_simulated": self.is_simulated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChatHistory(db.Model):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)
    message = db.Column(db.Text, nullable=False)
    context_symbol = db.Column(db.String(16), nullable=True)
    intent = db.Column(db.String(48), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="chat_messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "message": self.message,
            "context_symbol": self.context_symbol,
            "intent": self.intent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
