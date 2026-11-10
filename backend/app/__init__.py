import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.extensions import db
from app.routes.auth_routes import auth_bp
from app.routes.chat_routes import chat_bp
from app.routes.market_routes import market_bp
from app.routes.portfolio_routes import portfolio_bp
from app.routes.prediction_routes import prediction_bp
from app.routes.risk_routes import risk_bp
from app.seed import seed_database
from app.services.scheduler_service import start_verification_scheduler


def create_app(config_object=Config, auto_seed: bool = True, force_backtest: bool = True) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(chat_bp)

    @app.get("/api/health")
    def health_check():
        return jsonify(
            {
                "status": "ok",
                "app": "TradeWise AI Backend",
                "mode": "HYBRID_REAL_MARKET_AND_SIMULATED_TEST",
            }
        ), 200

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "Requested resource was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify({"error": "HTTP method not allowed for this endpoint."}), 405

    @app.errorhandler(500)
    def internal_error(_err):
        return jsonify({"error": "An unexpected internal server error occurred."}), 500

    with app.app_context():
        db.create_all()
        if auto_seed:
            seed_database(force_backtest=force_backtest)

    if app.config.get("ENABLE_BACKGROUND_SCHEDULER") and not app.config.get("TESTING"):
        start_verification_scheduler(app)

    return app
