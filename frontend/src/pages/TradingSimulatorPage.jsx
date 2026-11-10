import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Briefcase,
  DollarSign,
  Radio,
  RefreshCw,
  RotateCcw,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { DataSourceBadge } from "../components/SignalBadge";
import { StatCard } from "../components/StatCard";
import { useAuth } from "../context/AuthContext";

const PIE_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#38bdf8", "#a855f7", "#f43f5e", "#14b8a6"];

export function TradingSimulatorPage() {
  const { refreshUser } = useAuth();
  const [dataSource, setDataSource] = useState("REAL_MARKET");
  const [autoStream, setAutoStream] = useState(true);
  const [stocks, setStocks] = useState([]);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [order, setOrder] = useState({ symbol: "AAPL", side: "BUY", quantity: "5", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [lastTickAt, setLastTickAt] = useState("");
  const [feedback, setFeedback] = useState({ type: "", text: "" });

  const loadTradingState = useCallback(async () => {
    try {
      const [stRes, portRes, txRes] = await Promise.all([
        api.getStocks(dataSource),
        api.getPortfolio(dataSource === "REAL_MARKET"),
        api.getTransactions(50),
      ]);
      setStocks(stRes.stocks || []);
      setPortfolio(portRes);
      setTransactions(txRes.transactions || []);
      setLastTickAt(new Date().toLocaleTimeString());

      if (dataSource === "REAL_MARKET") {
        try {
          const q = await api.getLiveQuote(order.symbol, true);
          setSelectedQuote(q);
        } catch {
          setSelectedQuote(null);
        }
      } else {
        setSelectedQuote(null);
      }
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    }
  }, [dataSource, order.symbol]);

  useEffect(() => {
    loadTradingState();
  }, [loadTradingState]);

  // Real-time 5-second streaming quote & live P&L refresh when in REAL_MARKET mode
  useEffect(() => {
    if (!autoStream || dataSource !== "REAL_MARKET") return undefined;
    const timer = setInterval(() => {
      loadTradingState();
    }, 5000);
    return () => clearInterval(timer);
  }, [autoStream, dataSource, loadTradingState]);

  const activeStock =
    selectedQuote || stocks.find((s) => s.symbol === order.symbol);
  const livePrice = activeStock ? Number(activeStock.current_price) : 0;
  const qtyNum = Number(order.quantity) || 0;
  const estimatedCost = livePrice * qtyNum;

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFeedback({ type: "", text: "" });
    try {
      const res = await api.placeTrade({
        symbol: order.symbol,
        transaction_type: order.side,
        quantity: Number(order.quantity),
        data_source: dataSource,
        notes: order.notes,
      });
      setFeedback({ type: "success", text: res.message });
      setOrder((prev) => ({ ...prev, notes: "" }));
      await Promise.all([loadTradingState(), refreshUser()]);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async () => {
    setSubmitting(true);
    setFeedback({ type: "", text: "" });
    try {
      const res = await api.resetPortfolio();
      setFeedback({ type: "success", text: res.message });
      setConfirmReset(false);
      await Promise.all([loadTradingState(), refreshUser()]);
    } catch (err) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Real-Time Virtual Trading Simulator
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Execute instant virtual BUY/SELL orders at live real-time market prices with $100,000 practice funds.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800">
            <button
              onClick={() => setDataSource("REAL_MARKET")}
              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold ${
                dataSource === "REAL_MARKET"
                  ? "bg-white text-emerald-600 shadow-sm dark:bg-slate-900 dark:text-emerald-400"
                  : "text-slate-500"
              }`}
            >
              <Radio className="h-3.5 w-3.5" />
              Real-Time Prices
            </button>
            <button
              onClick={() => setDataSource("SIMULATED_TEST")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
                dataSource === "SIMULATED_TEST"
                  ? "bg-white text-amber-600 shadow-sm dark:bg-slate-900 dark:text-amber-400"
                  : "text-slate-500"
              }`}
            >
              Simulated Feed
            </button>
          </div>

          {!confirmReset ? (
            <button
              onClick={() => setConfirmReset(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset $100k
            </button>
          ) : (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs">
              <span className="font-medium text-rose-500">Reset all holdings?</span>
              <button
                onClick={handleReset}
                disabled={submitting}
                className="rounded-lg bg-rose-600 px-2.5 py-1 font-semibold text-white"
              >
                Confirm
              </button>
              <button onClick={() => setConfirmReset(false)} className="px-1.5 text-slate-400">
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Live Stream Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-800 dark:text-emerald-200">
        <div className="flex items-center gap-2">
          <Radio className={`h-4 w-4 ${autoStream && dataSource === "REAL_MARKET" ? "animate-pulse text-emerald-500" : "text-slate-400"}`} />
          <span>
            {dataSource === "REAL_MARKET"
              ? `Live Market Quotes active (auto-refresh every 5s · Last update: ${lastTickAt || "—"}). Virtual paper funds only—no real brokerage connection.`
              : "Using isolated Simulated Testing prices. Virtual paper funds only."}
          </span>
        </div>
        {dataSource === "REAL_MARKET" && (
          <div className="flex items-center gap-2">
            <label className="flex cursor-pointer items-center gap-1.5 font-semibold">
              <input
                type="checkbox"
                checked={autoStream}
                onChange={(e) => setAutoStream(e.target.checked)}
                className="rounded text-emerald-600"
              />
              Auto-Refresh 5s
            </label>
            <button onClick={loadTradingState} className="rounded-lg bg-emerald-600/20 p-1 hover:bg-emerald-600/30">
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {feedback.text && (
        <div
          className={`rounded-xl border px-4 py-2.5 text-xs font-medium ${
            feedback.type === "error"
              ? "border-rose-500/30 bg-rose-500/10 text-rose-500"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
          }`}
        >
          {feedback.text}
        </div>
      )}

      {/* Portfolio KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Virtual Equity"
          value={`$${Number(portfolio?.total_equity ?? 100000).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          trend={portfolio?.total_return_pct ?? 0}
          subtitle="Live holdings + virtual cash"
          icon={Briefcase}
          accent="indigo"
        />
        <StatCard
          title="Virtual Cash"
          value={`$${Number(portfolio?.virtual_cash_balance ?? 100000).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          subtitle="Available buying power"
          icon={DollarSign}
          accent="emerald"
        />
        <StatCard
          title="Unrealized P&L"
          value={`${(portfolio?.unrealized_pnl ?? 0) >= 0 ? "+" : "-"}$${Math.abs(portfolio?.unrealized_pnl ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          trend={portfolio?.unrealized_pnl_pct ?? 0}
          subtitle="Live mark-to-market"
          icon={TrendingUp}
          accent={(portfolio?.unrealized_pnl ?? 0) >= 0 ? "emerald" : "rose"}
        />
        <StatCard
          title="Realized P&L"
          value={`${(portfolio?.realized_pnl ?? 0) >= 0 ? "+" : "-"}$${Math.abs(portfolio?.realized_pnl ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          subtitle={`${portfolio?.transactions_count ?? 0} executed virtual trades`}
          icon={ArrowUpRight}
          accent="sky"
        />
      </div>

      {/* Live Order Ticket + Intraday Quote Chart */}
      <div className="grid gap-6 lg:grid-cols-3">
        <form onSubmit={handlePlaceOrder} className="fintech-card p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Instant Virtual Order
            </h3>
            <DataSourceBadge dataSource={dataSource} isSimulated={dataSource === "SIMULATED_TEST"} />
          </div>

          <div className="mt-4 flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
            {["BUY", "SELL"].map((side) => (
              <button
                key={side}
                type="button"
                onClick={() => setOrder({ ...order, side })}
                className={`flex-1 rounded-lg py-2 text-xs font-bold transition ${
                  order.side === side
                    ? side === "BUY"
                      ? "bg-emerald-600 text-white"
                      : "bg-rose-600 text-white"
                    : "text-slate-500"
                }`}
              >
                {side}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-3.5">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Stock Ticker
              </label>
              <select
                value={order.symbol}
                onChange={(e) => setOrder({ ...order, symbol: e.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-medium dark:border-slate-700 dark:bg-slate-800"
              >
                {stocks.map((s) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol} — ${s.current_price.toFixed(2)} ({s.day_change_pct >= 0 ? "+" : ""}{s.day_change_pct}%)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Quantity (Shares)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={order.quantity}
                onChange={(e) => setOrder({ ...order, quantity: e.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 font-mono text-sm outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
              />
              <div className="mt-1.5 flex gap-1.5">
                {[1, 5, 10, 25].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setOrder({ ...order, quantity: String(q) })}
                    className="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {q} sh
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl bg-slate-100/80 p-3 text-xs dark:bg-slate-800/70">
              <div className="flex justify-between">
                <span className="text-slate-500">Live Execution Price</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white tabular-nums">
                  ${livePrice > 0 ? livePrice.toFixed(2) : "—"}
                </span>
              </div>
              <div className="mt-1 flex justify-between">
                <span className="text-slate-500">Estimated Total</span>
                <span className="font-mono font-bold text-indigo-500 tabular-nums">
                  ${estimatedCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || livePrice <= 0}
              className={`w-full rounded-xl py-2.5 text-sm font-bold text-white transition disabled:opacity-60 ${
                order.side === "BUY" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-rose-600 hover:bg-rose-500"
              }`}
            >
              {submitting ? "Executing..." : `Execute ${order.side} @ $${livePrice.toFixed(2)}`}
            </button>
          </div>
        </form>

        {/* Live Intraday Quote Chart + Holdings */}
        <div className="space-y-6 lg:col-span-2">
          {selectedQuote?.intraday?.length > 0 && (
            <div className="fintech-card p-5">
              <div className="mb-2 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                    {selectedQuote.symbol} — Live Intraday 5m Price Action
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    High: ${selectedQuote.day_high.toFixed(2)} · Low: ${selectedQuote.day_low.toFixed(2)} · Prev Close: ${selectedQuote.previous_close.toFixed(2)}
                  </p>
                </div>
                <span className="font-mono text-lg font-bold text-emerald-500 tabular-nums">
                  ${selectedQuote.current_price.toFixed(2)}
                </span>
              </div>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={selectedQuote.intraday}>
                    <defs>
                      <linearGradient id="liveGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" vertical={false} />
                    <XAxis dataKey="time_label" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={22} />
                    <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={52} tickFormatter={(v) => `$${v}`} />
                    <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.94)", borderRadius: "10px", fontSize: "12px" }} />
                    <Area type="monotone" dataKey="close" name="Live Price ($)" stroke="#10b981" fill="url(#liveGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="fintech-card p-5">
            <div className="grid gap-6 md:grid-cols-5">
              <div className="md:col-span-3">
                <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
                  Open Virtual Holdings
                </h3>
                {portfolio?.holdings?.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                          <th className="py-2 font-medium">Stock</th>
                          <th className="py-2 font-medium">Qty</th>
                          <th className="py-2 font-medium">Avg Cost</th>
                          <th className="py-2 font-medium">Live Price</th>
                          <th className="py-2 font-medium">Unrealized P&L</th>
                          <th className="py-2 font-medium">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
                        {portfolio.holdings.map((h) => (
                          <tr key={`${h.symbol}-${h.data_source}`}>
                            <td className="py-2.5">
                              <span className="font-bold text-slate-900 dark:text-white">{h.symbol}</span>
                              <div className="mt-0.5">
                                <DataSourceBadge dataSource={h.data_source} isSimulated={h.is_simulated} />
                              </div>
                            </td>
                            <td className="py-2.5 font-mono">{h.quantity}</td>
                            <td className="py-2.5 font-mono">${h.average_buy_price.toFixed(2)}</td>
                            <td className="py-2.5 font-mono font-semibold">${h.current_price.toFixed(2)}</td>
                            <td className={`py-2.5 font-mono font-semibold ${h.unrealized_pnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                              {h.unrealized_pnl >= 0 ? "+" : "-"}${Math.abs(h.unrealized_pnl).toFixed(2)} ({h.unrealized_pnl_pct}%)
                            </td>
                            <td className="py-2.5">
                              <button
                                type="button"
                                onClick={() => {
                                  setDataSource(h.data_source);
                                  setOrder({ symbol: h.symbol, side: "SELL", quantity: String(h.quantity), notes: "" });
                                }}
                                className="rounded-lg bg-rose-500/15 px-2 py-1 text-[11px] font-semibold text-rose-500 hover:bg-rose-500/25"
                              >
                                Sell All
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No open positions yet.</p>
                )}
              </div>

              <div className="md:col-span-2">
                <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">
                  Allocation
                </h3>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={portfolio?.allocation || []} dataKey="value" nameKey="name" innerRadius={40} outerRadius={68} paddingAngle={3}>
                        {(portfolio?.allocation || []).map((_, idx) => (
                          <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.94)", borderRadius: "10px", fontSize: "12px" }} formatter={(v) => `$${Number(v).toLocaleString()}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="fintech-card p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
          Virtual Transaction Ledger
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="py-2 font-medium">Timestamp</th>
                <th className="py-2 font-medium">Type</th>
                <th className="py-2 font-medium">Stock</th>
                <th className="py-2 font-medium">Feed</th>
                <th className="py-2 font-medium">Qty</th>
                <th className="py-2 font-medium">Exec Price</th>
                <th className="py-2 font-medium">Total</th>
                <th className="py-2 font-medium">Realized P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td className="py-2.5 text-slate-500">{t.created_at?.slice(0, 19).replace("T", " ")}</td>
                  <td className="py-2.5">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        t.transaction_type === "BUY" ? "bg-emerald-500/15 text-emerald-500" : "bg-rose-500/15 text-rose-500"
                      }`}
                    >
                      {t.transaction_type === "BUY" ? <ArrowDownLeft className="h-3 w-3" /> : <ArrowUpRight className="h-3 w-3" />}
                      {t.transaction_type}
                    </span>
                  </td>
                  <td className="py-2.5 font-bold text-slate-900 dark:text-white">{t.symbol}</td>
                  <td className="py-2.5">
                    <DataSourceBadge dataSource={t.data_source} isSimulated={t.data_source === "SIMULATED_TEST"} />
                  </td>
                  <td className="py-2.5 font-mono">{t.quantity}</td>
                  <td className="py-2.5 font-mono">${t.price_per_share.toFixed(2)}</td>
                  <td className="py-2.5 font-mono">${t.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className={`py-2.5 font-mono font-semibold ${t.realized_pnl === null ? "text-slate-400" : t.realized_pnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                    {t.realized_pnl === null ? "—" : `${t.realized_pnl >= 0 ? "+" : "-"}$${Math.abs(t.realized_pnl).toFixed(2)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
