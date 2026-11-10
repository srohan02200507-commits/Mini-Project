import re

from app.extensions import db
from app.models import ChatHistory, Prediction, Stock
from app.services.accountability_service import compute_accountability_dashboard
from app.services.market_service import compute_technical_indicators, get_stock_dataframe
from app.services.risk_service import analyze_stock_risk
from app.services.trading_service import get_portfolio_summary

TRADING_GLOSSARY = {
    "rsi": (
        "**RSI (Relative Strength Index)** is a 0–100 momentum oscillator measuring how fast prices have moved recently. "
        "Values above 70 often suggest *overbought* conditions (price rose quickly), while values below 30 suggest *oversold* conditions."
    ),
    "sma": (
        "**SMA (Simple Moving Average)** calculates the average closing price over a set window (like 5, 20, or 50 days) "
        "to smooth out daily noise and reveal the underlying price trend."
    ),
    "ema": (
        "**EMA (Exponential Moving Average)** is similar to an SMA but gives higher weight to recent prices, making it react faster to new momentum shifts."
    ),
    "macd": (
        "**MACD (Moving Average Convergence Divergence)** compares a fast 12-day EMA against a slower 26-day EMA. "
        "When the MACD histogram turns positive, short-term upward momentum is accelerating relative to the longer trend."
    ),
    "bollinger": (
        "**Bollinger Bands** plot an upper and lower envelope 2 standard deviations around a 20-day moving average. "
        "Wider bands indicate higher volatility; prices near the upper/lower band show stretched moves."
    ),
    "volatility": (
        "**Volatility** measures how wildly a stock's price fluctuates over time. High volatility increases potential upside and downside risk alike."
    ),
    "drawdown": (
        "**Maximum Drawdown** is the largest percentage drop from a previous price peak to a subsequent trough—helping beginners visualize downside risk."
    ),
    "var": (
        "**Value at Risk (95% VaR)** estimates the daily loss threshold exceeded in only the worst 5% of historical days. Real losses can still exceed VaR."
    ),
    "mae": (
        "**MAE (Mean Absolute Error)** measures the average dollar gap `|actual_price - predicted_price|` across all verified predictions."
    ),
    "accountability": (
        "Our **Prediction Accountability Engine** records every AI prediction with a unique Prediction ID, target timestamp, and rationale, "
        "then automatically verifies it against actual market prices after the target time without overwriting history."
    ),
}


def _detect_symbol_in_message(message: str, fallback_symbol: str | None = None) -> str | None:
    upper_msg = message.upper()
    tokens = re.findall(r"\b[A-Z]{2,6}\b", upper_msg)
    known = {s.symbol for s in Stock.query.all()} | {"AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "JNJ", "XOM", "SPY"}

    for tok in tokens:
        if tok in known:
            return tok

    if fallback_symbol:
        return fallback_symbol.strip().upper()
    return None


def _match_glossary_term(lower_msg: str) -> str | None:
    for key, definition in TRADING_GLOSSARY.items():
        if re.search(rf"\b{re.escape(key)}\b", lower_msg):
            return definition
    if "moving average" in lower_msg:
        return TRADING_GLOSSARY["sma"]
    if "relative strength" in lower_msg:
        return TRADING_GLOSSARY["rsi"]
    return None


def generate_assistant_reply(user, message: str, context_symbol: str | None = None) -> tuple[str, str, str | None]:
    clean_msg = message.strip()
    lower_msg = clean_msg.lower()
    resolved_symbol = _detect_symbol_in_message(clean_msg, fallback_symbol=context_symbol)

    # 1. Safety / profit guarantee boundary
    if any(kw in lower_msg for kw in ["guarantee", "100% sure", "risk free", "get rich", "sure profit"]):
        reply = (
            "No trading system—including TradeWise AI—can guarantee profits, future accuracy, or eliminate risk. "
            "Every historical forecast is audited transparently in **Accountability Dashboard** and **Prediction History** "
            "(showing both CORRECT and INCORRECT calls), and virtual trades use practice funds only."
        )
        return reply, "risk_education", resolved_symbol

    # 2. Explain why a specific prediction was generated
    if any(kw in lower_msg for kw in ["why", "explain prediction", "reason", "up", "down", "sideways"]) and resolved_symbol:
        latest_pred = (
            Prediction.query.filter_by(stock_symbol=resolved_symbol)
            .order_by(Prediction.prediction_timestamp.desc(), Prediction.id.desc())
            .first()
        )
        if latest_pred:
            pred_dict = latest_pred.to_dict()
            patterns = "\n".join(
                f"- **{p['pattern']}** ({p['metric']} — *{p['signal']}*): {p['detail']}"
                for p in pred_dict.get("historical_patterns", [])[:4]
            )
            status_line = (
                f"Outcome: **{latest_pred.prediction_result}** "
                f"(Actual: ${latest_pred.actual_price:.2f} / {latest_pred.actual_direction}, Error: ${latest_pred.absolute_price_error:.2f})."
                if latest_pred.verification_status == "VERIFIED" and latest_pred.actual_price is not None
                else f"Status: **{latest_pred.verification_status}** (Target: {latest_pred.target_timestamp.isoformat()})."
            )
            reply = (
                f"### Prediction Explanation for {resolved_symbol} ({latest_pred.prediction_id})\n"
                f"- **Predicted Direction:** **{latest_pred.predicted_direction}** | **Target Price:** ${latest_pred.predicted_price:.2f} "
                f"(from ${latest_pred.starting_price:.2f}, {latest_pred.predicted_return_pct:+.2f}%)\n"
                f"- **Confidence Score:** {latest_pred.confidence_score:.1f}% | **Data Source:** {latest_pred.data_source}\n"
                f"- {status_line}\n\n"
                f"**Why AI Predicted {latest_pred.predicted_direction}:** {latest_pred.prediction_reason}\n\n"
                f"**Historical Patterns Observed:**\n{patterns}\n\n"
                f"**What Confidence Means:** {latest_pred.confidence_meaning}"
            )
            return reply, "explain_prediction", resolved_symbol

    # 3. Summarize prediction history / accountability performance
    if any(kw in lower_msg for kw in ["history", "accuracy", "accountability", "performance", "score", "report", "mae"]):
        dash = compute_accountability_dashboard(user_id=user.id)
        s = dash["summary"]
        best = dash["best_performing_stocks"][0] if dash["best_performing_stocks"] else None
        best_line = (
            f"Best-performing stock: **{best['symbol']}** ({best['accuracy_pct']}% accuracy, MAE ${best['mae']:.2f})."
            if best
            else ""
        )
        reply = (
            f"### Prediction Accountability Summary\n"
            f"- **Accountability Score:** {s['accountability_score']}/100\n"
            f"- **Direction Accuracy:** {s['direction_accuracy_pct']}% ({s['correct_predictions']} correct, {s['incorrect_predictions']} incorrect out of {s['verified_predictions']} verified; {s['pending_predictions']} pending excluded)\n"
            f"- **Mean Absolute Error (MAE):** ${s['mean_absolute_error']:.2f} ({s['mean_absolute_pct_error']}% MAPE)\n"
            f"{best_line}\n\n"
            f"*Note: Past verified scores do not guarantee future prediction accuracy.*"
        )
        return reply, "prediction_history", resolved_symbol

    # 4. Terminology / Glossary explanation
    glossary_match = _match_glossary_term(lower_msg)
    if glossary_match and any(kw in lower_msg for kw in ["what is", "what's", "explain", "mean", "define", "term"]):
        return f"{glossary_match}\n\nWant me to inspect live predictions or market patterns for a ticker like AAPL or NVDA?", "glossary", resolved_symbol

    # 5. User virtual portfolio summary
    if any(kw in lower_msg for kw in ["portfolio", "my holdings", "my cash", "profit", "loss", "pnl", "balance"]):
        p = get_portfolio_summary(user)
        holdings_txt = (
            ", ".join(f"{h['symbol']} ({h['quantity']:g} sh, P&L {h['unrealized_pnl']:+.2f})" for h in p["holdings"][:5])
            if p["holdings"]
            else "No open virtual positions yet."
        )
        reply = (
            f"### Virtual Portfolio Snapshot\n"
            f"- **Total Virtual Equity:** ${p['total_equity']:,.2f} (Return: {p['total_return_pct']:+.2f}%)\n"
            f"- **Virtual Cash Available:** ${p['virtual_cash_balance']:,.2f}\n"
            f"- **Unrealized P&L:** ${p['unrealized_pnl']:+,.2f} | **Realized P&L:** ${p['realized_pnl']:+,.2f}\n"
            f"- **Holdings:** {holdings_txt}"
        )
        return reply, "portfolio_summary", resolved_symbol

    # 6. Market trend & risk analysis for a local stock
    stock = Stock.query.filter_by(symbol=resolved_symbol).first() if resolved_symbol else None
    if stock and any(kw in lower_msg for kw in ["trend", "analy", "price", "risk", "how is", "doing", "outlook", "chart"]):
        df = get_stock_dataframe(stock.id)
        risk = analyze_stock_risk(stock)
        if not df.empty and len(df) >= 25:
            ind = compute_technical_indicators(df).iloc[-1]
            ret_5d = float(ind.get("return_5d", 0.0) or 0.0) * 100.0
            rsi = float(ind.get("rsi_14", 50.0) or 50.0)
            sma20 = float(ind.get("sma_20", stock.current_price) or stock.current_price)
            trend_dir = "above" if stock.current_price >= sma20 else "below"
            reply = (
                f"### Market Analysis (Simulated Test Feed): {stock.symbol}\n"
                f"- **Price:** ${stock.current_price:.2f} ({stock.day_change_pct:+.2f}% today, {ret_5d:+.2f}% 5D)\n"
                f"- **Trend Position:** Trading **{trend_dir}** 20-day SMA (${sma20:.2f}), 14-day RSI at **{rsi:.1f}**.\n"
                f"- **Risk Profile:** **{risk['risk_level']}** ({risk['annualized_volatility_pct']:.1f}% annualized vol, max drawdown {risk['max_drawdown_pct']:.2f}%)."
            )
            return reply, "market_trend", stock.symbol

    if glossary_match:
        return glossary_match, "glossary", resolved_symbol

    reply = (
        "Hi! I'm **TradeWise Assistant**. Ask me about:\n"
        "- **Prediction Explanations:** *\"Why did AI predict UP/DOWN/SIDEWAYS for AAPL?\"*\n"
        "- **Accountability Metrics:** *\"Summarize our prediction accuracy and MAE\"*\n"
        "- **Trading Terms:** *\"What is RSI?\"*, *\"What is MAE?\"*, or *\"What is Volatility?\"*\n"
        "- **Virtual Portfolio:** *\"How is my virtual portfolio performing?\"*"
    )
    return reply, "general_help", resolved_symbol


def process_chat_message(user, message: str, context_symbol: str | None = None) -> tuple[ChatHistory, ChatHistory]:
    user_entry = ChatHistory(
        user_id=user.id,
        role="user",
        message=message.strip(),
        context_symbol=context_symbol.upper() if context_symbol else None,
        intent="user_query",
    )
    db.session.add(user_entry)

    reply_text, intent, resolved_symbol = generate_assistant_reply(user, message, context_symbol=context_symbol)
    assistant_entry = ChatHistory(
        user_id=user.id,
        role="assistant",
        message=reply_text,
        context_symbol=resolved_symbol,
        intent=intent,
    )
    db.session.add(assistant_entry)
    db.session.commit()
    return user_entry, assistant_entry
