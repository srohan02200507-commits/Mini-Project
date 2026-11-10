from app.extensions import db
from app.models import Stock, Transaction, User, VirtualPortfolio
from app.services.market_provider import (
    MarketDataUnavailableError,
    fetch_real_time_quote,
    fetch_real_time_quotes,
)


def _resolve_trade_instrument(symbol: str, data_source: str) -> dict:
    clean_symbol = symbol.strip().upper()
    source = (data_source or "REAL_MARKET").strip().upper()
    local_stock = Stock.query.filter_by(symbol=clean_symbol).first()

    if source == "SIMULATED_TEST":
        if not local_stock:
            raise ValueError(f"Simulated stock '{clean_symbol}' was not found.")
        return {
            "symbol": local_stock.symbol,
            "name": local_stock.name,
            "sector": local_stock.sector,
            "stock_id": local_stock.id,
            "price": float(local_stock.current_price),
            "data_source": "SIMULATED_TEST",
            "is_simulated": True,
        }

    # REAL_MARKET mode: fetch live quote directly from Yahoo Finance
    try:
        quote = fetch_real_time_quote(clean_symbol, include_intraday=False)
    except MarketDataUnavailableError as exc:
        raise MarketDataUnavailableError(
            f"Live real-time quote for {clean_symbol} is currently unavailable ({exc}). "
            "Switch to Simulated Testing Mode or try again when connected."
        ) from exc

    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "sector": local_stock.sector if local_stock else "Real-Time Equities",
        "stock_id": local_stock.id if local_stock else None,
        "price": float(quote["current_price"]),
        "data_source": "REAL_MARKET",
        "is_simulated": False,
    }


def execute_virtual_trade(
    user: User,
    symbol: str,
    side: str,
    quantity: float,
    data_source: str = "REAL_MARKET",
    notes: str | None = None,
) -> tuple[Transaction, VirtualPortfolio | None]:
    side = side.strip().upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("Transaction type must be BUY or SELL.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    instrument = _resolve_trade_instrument(symbol, data_source)
    clean_symbol = instrument["symbol"]
    source = instrument["data_source"]
    price = instrument["price"]
    total_amount = round(price * quantity, 2)

    holding = VirtualPortfolio.query.filter_by(
        user_id=user.id,
        stock_symbol=clean_symbol,
        data_source=source,
    ).first()

    if side == "BUY":
        if user.virtual_cash_balance + 1e-6 < total_amount:
            raise ValueError(
                f"Insufficient virtual cash balance (${user.virtual_cash_balance:,.2f} available, "
                f"${total_amount:,.2f} required)."
            )

        user.virtual_cash_balance = round(user.virtual_cash_balance - total_amount, 2)
        if holding:
            prev_cost = holding.quantity * holding.average_buy_price
            new_qty = holding.quantity + quantity
            holding.average_buy_price = round((prev_cost + total_amount) / new_qty, 4)
            holding.quantity = round(new_qty, 4)
            holding.last_known_price = round(price, 2)
        else:
            holding = VirtualPortfolio(
                user_id=user.id,
                stock_id=instrument["stock_id"],
                stock_symbol=clean_symbol,
                stock_name=instrument["name"],
                sector=instrument["sector"],
                data_source=source,
                quantity=round(quantity, 4),
                average_buy_price=round(price, 4),
                last_known_price=round(price, 2),
            )
            db.session.add(holding)

        tx = Transaction(
            user_id=user.id,
            stock_id=instrument["stock_id"],
            stock_symbol=clean_symbol,
            stock_name=instrument["name"],
            data_source=source,
            transaction_type="BUY",
            quantity=round(quantity, 4),
            price_per_share=round(price, 2),
            total_amount=total_amount,
            realized_pnl=None,
            notes=notes or f"[{source}] Virtual BUY {quantity:g} {clean_symbol} @ ${price:.2f}",
            is_simulated=True,
        )
        db.session.add(tx)
        db.session.commit()
        return tx, holding

    # SELL
    if not holding or holding.quantity + 1e-6 < quantity:
        owned = holding.quantity if holding else 0.0
        raise ValueError(
            f"Insufficient shares of {clean_symbol} ({source}) to sell ({owned:g} owned, {quantity:g} requested)."
        )

    sell_qty = min(quantity, holding.quantity)
    proceeds = round(price * sell_qty, 2)
    realized_pnl = round((price - holding.average_buy_price) * sell_qty, 2)

    user.virtual_cash_balance = round(user.virtual_cash_balance + proceeds, 2)
    remaining_qty = round(holding.quantity - sell_qty, 4)
    if remaining_qty <= 0.0001:
        db.session.delete(holding)
        updated_holding = None
    else:
        holding.quantity = remaining_qty
        holding.last_known_price = round(price, 2)
        updated_holding = holding

    tx = Transaction(
        user_id=user.id,
        stock_id=instrument["stock_id"],
        stock_symbol=clean_symbol,
        stock_name=instrument["name"],
        data_source=source,
        transaction_type="SELL",
        quantity=round(sell_qty, 4),
        price_per_share=round(price, 2),
        total_amount=proceeds,
        realized_pnl=realized_pnl,
        notes=notes or f"[{source}] Virtual SELL {sell_qty:g} {clean_symbol} @ ${price:.2f}",
        is_simulated=True,
    )
    db.session.add(tx)
    db.session.commit()
    return tx, updated_holding


def get_portfolio_summary(user: User, refresh_live: bool = False) -> dict:
    holdings = (
        VirtualPortfolio.query.filter_by(user_id=user.id)
        .order_by(VirtualPortfolio.stock_symbol.asc())
        .all()
    )

    live_prices = {}
    if refresh_live:
        real_symbols = sorted({h.stock_symbol for h in holdings if h.data_source == "REAL_MARKET"})
        if real_symbols:
            quotes_payload = fetch_real_time_quotes(real_symbols)
            for q in quotes_payload.get("quotes", []):
                live_prices[q["symbol"]] = float(q["current_price"])
            for h in holdings:
                if h.data_source == "REAL_MARKET" and h.stock_symbol in live_prices:
                    h.last_known_price = round(live_prices[h.stock_symbol], 2)
            if live_prices:
                db.session.commit()

    holding_dicts = [
        h.to_dict(live_price=live_prices.get(h.stock_symbol) if h.data_source == "REAL_MARKET" else None)
        for h in holdings
    ]

    invested_value = round(sum(h["market_value"] for h in holding_dicts), 2)
    cost_basis = round(sum(h["cost_basis"] for h in holding_dicts), 2)
    unrealized_pnl = round(invested_value - cost_basis, 2)
    unrealized_pnl_pct = round((unrealized_pnl / cost_basis) * 100.0, 2) if cost_basis > 0 else 0.0

    transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .all()
    )
    realized_pnl = round(
        sum(t.realized_pnl for t in transactions if t.realized_pnl is not None),
        2,
    )

    cash_balance = round(float(user.virtual_cash_balance), 2)
    total_equity = round(cash_balance + invested_value, 2)
    initial_cash = round(float(user.initial_cash_balance), 2)
    total_pnl = round(total_equity - initial_cash, 2)
    total_return_pct = round((total_pnl / initial_cash) * 100.0, 2) if initial_cash > 0 else 0.0

    sector_map = {}
    for h in holding_dicts:
        sec = h.get("sector") or "Equities"
        sector_map[sec] = round(sector_map.get(sec, 0.0) + h["market_value"], 2)

    allocation = [
        {"name": "Virtual Cash", "value": cash_balance},
        *[{"name": k, "value": v} for k, v in sorted(sector_map.items())],
    ]

    return {
        "virtual_cash_balance": cash_balance,
        "initial_cash_balance": initial_cash,
        "invested_value": invested_value,
        "cost_basis": cost_basis,
        "total_equity": total_equity,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "realized_pnl": realized_pnl,
        "total_pnl": total_pnl,
        "total_return_pct": total_return_pct,
        "holdings_count": len(holding_dicts),
        "holdings": holding_dicts,
        "allocation": allocation,
        "transactions_count": len(transactions),
        "is_simulated": True,
        "disclaimer": (
            "Virtual trading simulator executes paper trades with virtual funds ($100,000 start). "
            "No real brokerage accounts or real money orders are executed."
        ),
    }


def reset_virtual_account(user: User) -> dict:
    VirtualPortfolio.query.filter_by(user_id=user.id).delete()
    Transaction.query.filter_by(user_id=user.id).delete()
    user.virtual_cash_balance = user.initial_cash_balance
    db.session.commit()
    return get_portfolio_summary(user)
