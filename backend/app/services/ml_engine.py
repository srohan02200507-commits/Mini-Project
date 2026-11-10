from datetime import datetime, timedelta, timezone
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.market_provider import get_market_series
from app.services.market_service import compute_technical_indicators, next_trading_day

MODEL_NAME = "TradeWise Ensemble (GBR + RF + Ridge)"
MODEL_VERSION = "v2.1.0"

FEATURE_COLUMNS = [
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "price_vs_sma5",
    "price_vs_sma20",
    "sma5_vs_sma20",
    "macd",
    "macd_hist",
    "rsi_14",
    "bb_pct",
    "volatility_20",
    "volume_ratio",
    "hl_spread_pct",
]


def _classify_direction_from_return(return_pct: float, tolerance_pct: float) -> str:
    if return_pct > tolerance_pct:
        return "UP"
    if return_pct < -tolerance_pct:
        return "DOWN"
    return "SIDEWAYS"


def _build_full_explanation(
    latest_row: pd.Series,
    predicted_direction: str,
    pred_return_pct: float,
    prob_up: float,
    val_acc: float,
    val_mae_pct: float,
    confidence_score: float,
    gbr_ret_pct: float,
    ridge_ret_pct: float,
    tolerance_pct: float,
) -> dict:
    rsi = float(latest_row.get("rsi_14", 50.0))
    p_sma5 = float(latest_row.get("price_vs_sma5", 0.0)) * 100.0
    p_sma20 = float(latest_row.get("price_vs_sma20", 0.0)) * 100.0
    sma_cross = float(latest_row.get("sma5_vs_sma20", 0.0)) * 100.0
    macd_hist = float(latest_row.get("macd_hist", 0.0))
    vol_pct = float(latest_row.get("volatility_20", 20.0) or 20.0)
    ret_5d = float(latest_row.get("return_5d", 0.0)) * 100.0
    ret_10d = float(latest_row.get("return_10d", 0.0)) * 100.0
    bb_pct = float(latest_row.get("bb_pct", 0.5) if pd.notna(latest_row.get("bb_pct")) else 0.5)
    vol_ratio = float(latest_row.get("volume_ratio", 1.0) if pd.notna(latest_row.get("volume_ratio")) else 1.0)

    if predicted_direction == "UP":
        direction_rationale = (
            f"Projected return of {pred_return_pct:+.2f}% exceeds the +{tolerance_pct:.2f}% sideways band, "
            f"supported by an upward probability of {prob_up * 100:.1f}% across the ensemble."
        )
    elif predicted_direction == "DOWN":
        direction_rationale = (
            f"Projected return of {pred_return_pct:+.2f}% falls below the -{tolerance_pct:.2f}% sideways band, "
            f"with downward probability of {(1.0 - prob_up) * 100:.1f}% across the ensemble."
        )
    else:
        direction_rationale = (
            f"Projected move of {pred_return_pct:+.2f}% lies inside the +/-{tolerance_pct:.2f}% tolerance band "
            f"(upward probability {prob_up * 100:.1f}%), indicating range-bound SIDEWAYS consolidation."
        )

    prediction_reason = (
        f"AI predicted {predicted_direction} (GBR: {gbr_ret_pct:+.2f}%, Ridge: {ridge_ret_pct:+.2f}%). "
        f"{direction_rationale} Key observed readings: 14-day RSI at {rsi:.1f}, 5-day vs 20-day SMA spread "
        f"of {sma_cross:+.2f}%, and 5-day return of {ret_5d:+.2f}%."
    )

    historical_patterns = [
        {
            "pattern": "Moving Average Trend (SMA 5 vs SMA 20)",
            "metric": f"{sma_cross:+.2f}%",
            "signal": "Bullish" if sma_cross > 0.35 else ("Bearish" if sma_cross < -0.35 else "Neutral"),
            "detail": (
                "5-day average sits above 20-day average, showing short-term upward trend."
                if sma_cross > 0.35
                else (
                    "5-day average trails below 20-day average, reflecting short-term downward pressure."
                    if sma_cross < -0.35
                    else "Short and medium moving averages are tightly converged, typical of sideways range behavior."
                )
            ),
        },
        {
            "pattern": "14-Day RSI Momentum Regime",
            "metric": f"{rsi:.1f}",
            "signal": "Bullish" if rsi < 40 else ("Bearish" if rsi > 66 else "Neutral"),
            "detail": (
                "RSI below 40 suggests oversold mean-reversion pressure."
                if rsi < 40
                else (
                    "RSI above 66 indicates stretched momentum vulnerable to pullback."
                    if rsi > 66
                    else "RSI sits in neutral territory (40–66), indicating balanced buying/selling pressure."
                )
            ),
        },
        {
            "pattern": "Multi-Day Price Momentum (5D / 10D)",
            "metric": f"{ret_5d:+.2f}% / {ret_10d:+.2f}%",
            "signal": "Bullish" if ret_5d > 0.5 else ("Bearish" if ret_5d < -0.5 else "Neutral"),
            "detail": f"Price sits {p_sma5:+.2f}% vs 5-day SMA and {p_sma20:+.2f}% vs 20-day SMA.",
        },
        {
            "pattern": "Bollinger Band & MACD Histogram",
            "metric": f"BB {bb_pct * 100:.0f}% / MACD {macd_hist:+.3f}",
            "signal": "Bullish" if macd_hist > 0 else ("Bearish" if macd_hist < 0 else "Neutral"),
            "detail": (
                f"Price occupies the {bb_pct * 100:.0f}th percentile of its 20-day Bollinger channel "
                f"with trading volume at {vol_ratio:.2f}x the 20-day average."
            ),
        },
    ]

    confidence_meaning = (
        f"The {confidence_score:.1f}% confidence score reflects three measurable inputs: "
        f"(1) out-of-sample chronological validation directional accuracy ({val_acc * 100:.1f}% across the held-out 20% window, "
        f"validation MAE {val_mae_pct:.2f}%), (2) ensemble classifier probability distance from 50/50 uncertainty "
        f"({prob_up * 100:.1f}% upward probability), and (3) agreement between non-linear GBR ({gbr_ret_pct:+.2f}%) "
        f"and linear Ridge ({ridge_ret_pct:+.2f}%) forecasts. It is a statistical estimate, never a guarantee."
    )

    invalidation_factors = [
        f"Realized 20-day annualized volatility is {vol_pct:.1f}%—larger daily swings can cause actual price to cross outside predicted bounds.",
        "Unscheduled macro announcements, earnings surprises, or sector shocks are not visible in historical OHLCV price patterns.",
        (
            f"Cross-model disagreement detected (GBR {gbr_ret_pct:+.2f}% vs Ridge {ridge_ret_pct:+.2f}%), increasing forecast uncertainty."
            if gbr_ret_pct * ridge_ret_pct <= 0
            else f"Overfitting or regime shift risk: validation MAE on recent bars was {val_mae_pct:.2f}%."
        ),
        (
            "Price sits near extreme Bollinger Band / RSI levels where sudden mean-reversion reversals frequently occur."
            if (rsi > 68 or rsi < 32 or bb_pct > 0.9 or bb_pct < 0.1)
            else "Low-magnitude moves near the +/-0.50% tolerance threshold can flip between UP/DOWN and SIDEWAYS."
        ),
    ]

    return {
        "prediction_reason": prediction_reason,
        "historical_patterns": historical_patterns,
        "confidence_meaning": confidence_meaning,
        "invalidation_factors": invalidation_factors,
    }


def run_ml_prediction_from_df(
    df: pd.DataFrame,
    horizon_days: int = 1,
    horizon_hours: int | None = None,
    tolerance_pct: float = 0.50,
    prediction_timestamp: datetime | None = None,
    target_timestamp: datetime | None = None,
) -> dict:
    if df.empty or len(df) < 75:
        raise ValueError("Insufficient historical market data (minimum 75 trading bars required for ML modeling).")

    feat_df = compute_technical_indicators(df)
    step_bars = max(1, int(horizon_days))
    feat_df["target_return"] = (feat_df["close"].shift(-step_bars) / feat_df["close"]) - 1.0
    target_pct = feat_df["target_return"] * 100.0
    feat_df["target_dir"] = np.where(
        target_pct > tolerance_pct,
        "UP",
        np.where(target_pct < -tolerance_pct, "DOWN", "SIDEWAYS"),
    )

    latest_row = feat_df.iloc[-1]
    X_latest = feat_df.iloc[[-1]][FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)

    supervised = feat_df.iloc[50:-step_bars].copy()
    supervised[FEATURE_COLUMNS] = supervised[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    supervised = supervised.dropna(subset=["target_return"])

    if len(supervised) < 20:
        raise ValueError("Insufficient post-warmup market bars to fit chronological ML pipeline.")

    X = supervised[FEATURE_COLUMNS]
    y_reg = supervised["target_return"].astype(float)
    y_dir = supervised["target_dir"].astype(str)

    # Strict chronological split BEFORE fitting scalers or models
    split_idx = max(15, int(len(supervised) * 0.8))
    if split_idx >= len(supervised) - 3:
        split_idx = len(supervised) - 4

    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_reg_train, y_reg_val = y_reg.iloc[:split_idx], y_reg.iloc[split_idx:]
    y_dir_train, y_dir_val = y_dir.iloc[:split_idx], y_dir.iloc[split_idx:]

    gbr_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", GradientBoostingRegressor(n_estimators=70, max_depth=3, learning_rate=0.05, random_state=42)),
        ]
    )
    ridge_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=5.0)),
        ]
    )

    gbr_pipe.fit(X_train, y_reg_train)
    ridge_pipe.fit(X_train, y_reg_train)

    val_pred_reg = 0.65 * gbr_pipe.predict(X_val) + 0.35 * ridge_pipe.predict(X_val)
    val_mae = float(mean_absolute_error(y_reg_val, val_pred_reg))

    def _fit_and_predict_3class(X_tr, y_tr, X_eval):
        classes_present = np.unique(y_tr)
        if len(classes_present) < 2:
            only_cls = str(classes_present[0])
            probs = np.zeros((len(X_eval), 3))
            idx_map = {"DOWN": 0, "SIDEWAYS": 1, "UP": 2}
            probs[:, idx_map.get(only_cls, 1)] = 1.0
            return probs

        rf = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", RandomForestClassifier(n_estimators=90, max_depth=5, random_state=42)),
            ]
        )
        lr = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=500, C=0.5, random_state=42)),
            ]
        )
        rf.fit(X_tr, y_tr)
        lr.fit(X_tr, y_tr)
        rf_p = rf.predict_proba(X_eval)
        lr_p = lr.predict_proba(X_eval)

        aligned = np.zeros((len(X_eval), 3))
        order = ["DOWN", "SIDEWAYS", "UP"]
        for i, cls_name in enumerate(order):
            if cls_name in rf.classes_:
                aligned[:, i] += 0.60 * rf_p[:, list(rf.classes_).index(cls_name)]
            if cls_name in lr.classes_:
                aligned[:, i] += 0.40 * lr_p[:, list(lr.classes_).index(cls_name)]
        return aligned

    dir_order = ["DOWN", "SIDEWAYS", "UP"]
    val_class_probs = _fit_and_predict_3class(X_train, y_dir_train, X_val)
    val_pred_dirs = [dir_order[int(i)] for i in np.argmax(val_class_probs, axis=1)]
    val_acc = float(accuracy_score(y_dir_val, val_pred_dirs))

    # Refit on full available historical training set for next-step prediction
    gbr_pipe.fit(X, y_reg)
    ridge_pipe.fit(X, y_reg)
    gbr_ret = float(gbr_pipe.predict(X_latest)[0])
    ridge_ret = float(ridge_pipe.predict(X_latest)[0])
    blended_ret = float(np.clip(0.65 * gbr_ret + 0.35 * ridge_ret, -0.06, 0.06))

    latest_probs = _fit_and_predict_3class(X, y_dir, X_latest)[0]
    best_idx = int(np.argmax(latest_probs))
    predicted_direction = dir_order[best_idx]
    prob_best = float(latest_probs[best_idx])
    prob_up = float(latest_probs[2])

    # Ensure continuous price forecast stays consistent with predicted 3-class direction
    tol_dec = tolerance_pct / 100.0
    if predicted_direction == "UP" and blended_ret <= tol_dec:
        blended_ret = tol_dec + 0.0015
    elif predicted_direction == "DOWN" and blended_ret >= -tol_dec:
        blended_ret = -(tol_dec + 0.0015)
    elif predicted_direction == "SIDEWAYS" and abs(blended_ret) > tol_dec:
        blended_ret = float(np.clip(blended_ret, -tol_dec * 0.8, tol_dec * 0.8))

    pred_return_pct = blended_ret * 100.0
    starting_price = float(latest_row["close"])
    predicted_price = max(1.0, starting_price * (1.0 + blended_ret))

    # Confidence calibrated from winning class margin, validation accuracy, and model agreement
    directional_edge = max(0.0, (prob_best - 0.34) / 0.66)
    model_agreement = 1.0 if (gbr_ret * ridge_ret > 0) else 0.35
    raw_conf = 44.0 + (directional_edge * 28.0) + (val_acc * 16.0) + (model_agreement * 6.0)
    confidence_score = float(np.clip(raw_conf, 38.0, 91.0))

    explanation = _build_full_explanation(
        latest_row=latest_row,
        predicted_direction=predicted_direction,
        pred_return_pct=pred_return_pct,
        prob_up=prob_up,
        val_acc=val_acc,
        val_mae_pct=val_mae * 100.0,
        confidence_score=confidence_score,
        gbr_ret_pct=gbr_ret * 100.0,
        ridge_ret_pct=ridge_ret * 100.0,
        tolerance_pct=tolerance_pct,
    )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    pred_ts = prediction_timestamp or now_utc

    if target_timestamp is None:
        if horizon_hours is not None and horizon_hours > 0:
            tgt_ts = pred_ts + timedelta(hours=int(horizon_hours))
            horizon_label = f"{int(horizon_hours)}H"
        else:
            last_bar_date = latest_row["date"]
            if isinstance(last_bar_date, pd.Timestamp):
                last_bar_date = last_bar_date.date()
            tgt_date = last_bar_date
            for _ in range(step_bars):
                tgt_date = next_trading_day(tgt_date)
            tgt_ts = datetime.combine(tgt_date, pred_ts.time())
            horizon_label = f"{step_bars}D"
    else:
        tgt_ts = target_timestamp
        horizon_label = f"{step_bars}D"

    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "starting_price": round(starting_price, 2),
        "predicted_price": round(predicted_price, 2),
        "predicted_return_pct": round(pred_return_pct, 2),
        "predicted_direction": predicted_direction,
        "confidence_score": round(confidence_score, 1),
        "prediction_timestamp": pred_ts,
        "target_timestamp": tgt_ts,
        "horizon_label": horizon_label,
        "tolerance_pct": round(tolerance_pct, 2),
        "prediction_reason": explanation["prediction_reason"],
        "historical_patterns": explanation["historical_patterns"],
        "confidence_meaning": explanation["confidence_meaning"],
        "invalidation_factors": explanation["invalidation_factors"],
        "validation_metrics": {
            "validation_directional_accuracy_pct": round(val_acc * 100.0, 1),
            "validation_mae_pct": round(val_mae * 100.0, 2),
            "prob_up_pct": round(prob_up * 100.0, 1),
        },
        "latest_indicators": {
            "rsi_14": round(float(latest_row.get("rsi_14", 50.0)), 2),
            "sma_5": round(float(latest_row.get("sma_5", starting_price)), 2),
            "sma_20": round(float(latest_row.get("sma_20", starting_price)), 2),
            "sma_50": round(float(latest_row.get("sma_50", starting_price)), 2),
            "macd": round(float(latest_row.get("macd", 0.0)), 3),
            "macd_signal": round(float(latest_row.get("macd_signal", 0.0)), 3),
            "volatility_20": round(float(latest_row.get("volatility_20", 20.0) or 20.0), 2),
        },
    }


def generate_live_prediction(
    symbol: str,
    data_source: str = "REAL_MARKET",
    horizon_days: int = 1,
    horizon_hours: int | None = None,
    tolerance_pct: float = 0.50,
    prediction_timestamp: datetime | None = None,
    target_timestamp: datetime | None = None,
) -> tuple[dict, dict]:
    stock_meta, df = get_market_series(symbol, data_source=data_source)
    forecast = run_ml_prediction_from_df(
        df=df,
        horizon_days=horizon_days,
        horizon_hours=horizon_hours,
        tolerance_pct=tolerance_pct,
        prediction_timestamp=prediction_timestamp,
        target_timestamp=target_timestamp,
    )
    return stock_meta, forecast


def serialize_json_list(items: list) -> str:
    return json.dumps(items)
