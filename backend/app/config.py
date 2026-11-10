import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    SECRET_KEY = os.environ.get("TRADEWISE_SECRET_KEY", "tradewise-ai-dev-secret-key-2026")
    JWT_SECRET_KEY = os.environ.get("TRADEWISE_JWT_SECRET", "tradewise-ai-jwt-secret-key-2026")
    JWT_EXPIRATION = timedelta(hours=24)

    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'tradewise.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    INITIAL_VIRTUAL_CASH = 100000.0

    # Prediction Accountability Engine configuration
    DEFAULT_DATA_SOURCE = os.environ.get("TRADEWISE_DATA_SOURCE", "REAL_MARKET")
    SIDEWAYS_TOLERANCE_PCT = float(os.environ.get("TRADEWISE_TOLERANCE_PCT", "0.50"))
    MODEL_NAME = "TradeWise Ensemble (GBR + RF + Ridge)"
    MODEL_VERSION = "v2.1.0"

    # Background verification scheduler settings
    ENABLE_BACKGROUND_SCHEDULER = os.environ.get("TRADEWISE_ENABLE_SCHEDULER", "true").lower() == "true"
    SCHEDULER_INTERVAL_SECONDS = int(os.environ.get("TRADEWISE_SCHEDULER_INTERVAL", "60"))

    SIMULATION_DISCLAIMER = (
        "Simulated testing data is strictly separated from real market data. "
        "Nothing in TradeWise AI guarantees future prediction accuracy or returns."
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ENABLE_BACKGROUND_SCHEDULER = False
