import { useCallback, useEffect, useState } from "react";
import { ArrowRight, GitCompare, Target, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { PredictionDetailModal } from "../components/PredictionDetailModal";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "../components/SignalBadge";
import { StatCard } from "../components/StatCard";

const COMPARE_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "SPY"];

export function PredictionComparisonPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [dataSource, setDataSource] = useState("");
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPred, setSelectedPred] = useState(null);

  const loadComparison = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getSymbolComparison(symbol, dataSource);
      setComparison(res);
    } finally {
      setLoading(false);
    }
  }, [symbol, dataSource]);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  const predictions = comparison?.predictions || [];
  const chartData = predictions.map((p) => ({
    id: p.prediction_id.slice(-6),
    full_id: p.prediction_id,
    date: p.target_date,
    starting_price: p.starting_price,
    predicted_price: p.predicted_price,
    actual_price: p.actual_price,
    price_difference: p.price_difference,
    abs_error: p.absolute_price_error,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Prediction Comparison & Error Visualizer
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Compare Starting Price, AI Predicted Price, Actual Market Price, and exact price error across predictions for a stock.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
          >
            {COMPARE_SYMBOLS.map((s) => (
              <option key={s} value={s}>
                Stock: {s}
              </option>
            ))}
          </select>

          <select
            value={dataSource}
            onChange={(e) => setDataSource(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
          >
            <option value="">All Data Sources</option>
            <option value="REAL_MARKET">Real Market Only</option>
            <option value="SIMULATED_TEST">Simulated Test Only</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title={`${symbol} Predictions Tracked`}
          value={comparison?.total_predictions ?? 0}
          subtitle={`${comparison?.verified_predictions ?? 0} verified`}
          icon={GitCompare}
          accent="indigo"
        />
        <StatCard
          title={`${symbol} Direction Accuracy`}
          value={`${comparison?.direction_accuracy_pct ?? 0}%`}
          subtitle={`${comparison?.correct_predictions ?? 0} correct direction calls`}
          icon={Target}
          accent="emerald"
        />
        <StatCard
          title={`${symbol} Mean Absolute Error`}
          value={`$${Number(comparison?.mean_absolute_error ?? 0).toFixed(2)}`}
          subtitle="Average |Actual - Predicted|"
          icon={TrendingUp}
          accent="amber"
        />
      </div>

      {loading ? (
        <div className="fintech-card py-14 text-center text-xs text-slate-500">
          Loading comparison charts for {symbol}...
        </div>
      ) : predictions.length === 0 ? (
        <div className="fintech-card py-14 text-center text-xs text-slate-500">
          No recorded predictions found for {symbol}. Generate one in AI Predictions Studio!
        </div>
      ) : (
        <>
          {/* Chart 1: Starting vs Predicted vs Actual Price Line Comparison */}
          <div className="fintech-card p-5">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Starting vs. AI Predicted vs. Actual Stock Price ({symbol})
            </h3>
            <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
              Each point represents an individual recorded forecast ordered chronologically
            </p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v?.slice(5)} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `$${v}`} width={58} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.94)",
                      borderRadius: "10px",
                      fontSize: "12px",
                    }}
                    formatter={(val, name) => [val !== null ? `$${Number(val).toFixed(2)}` : "Pending", name]}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Line
                    type="monotone"
                    dataKey="starting_price"
                    name="Starting Price ($)"
                    stroke="#94a3b8"
                    strokeWidth={1.8}
                    strokeDasharray="4 4"
                    dot={{ r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="predicted_price"
                    name="AI Predicted Price ($)"
                    stroke="#6366f1"
                    strokeWidth={2.5}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="actual_price"
                    name="Actual Price ($)"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    connectNulls={false}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Price Difference & Absolute Error */}
          <div className="fintech-card p-5">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Price Difference (Actual − Predicted $) & Absolute Error
            </h3>
            <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
              Values near $0.00 indicate tight price precision; bars show signed miss and magnitude
            </p>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData.filter((d) => d.abs_error !== null)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v?.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `$${v}`} width={52} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.94)",
                      borderRadius: "10px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <ReferenceLine y={0} stroke="#64748b" />
                  <Bar dataKey="price_difference" name="Actual - Predicted ($)" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="abs_error" name="Absolute Error ($)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Side-by-Side Comparison Cards */}
          <div className="grid gap-4 md:grid-cols-2">
            {predictions.map((p) => (
              <div
                key={p.prediction_id}
                onClick={() => setSelectedPred(p)}
                className="fintech-card-hover cursor-pointer p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-500">{p.prediction_id}</span>
                    <DataSourceBadge dataSource={p.data_source} isSimulated={p.is_simulated} />
                  </div>
                  <ResultBadge status={p.verification_status} result={p.prediction_result} />
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs tabular-nums">
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5 dark:bg-slate-800/60">
                    <span className="text-[10px] text-slate-400 block">Start</span>
                    <span className="font-mono font-semibold">${p.starting_price.toFixed(2)}</span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
                  <div className="rounded-lg bg-indigo-500/10 px-2.5 py-1.5">
                    <span className="text-[10px] text-indigo-400 block">Predicted</span>
                    <span className="font-mono font-bold text-indigo-600 dark:text-indigo-300">
                      ${p.predicted_price.toFixed(2)} ({p.predicted_direction})
                    </span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
                  <div className="rounded-lg bg-emerald-500/10 px-2.5 py-1.5">
                    <span className="text-[10px] text-emerald-500 block">Actual</span>
                    <span className="font-mono font-bold text-emerald-600 dark:text-emerald-300">
                      {p.actual_price !== null
                        ? `$${p.actual_price.toFixed(2)} (${p.actual_direction})`
                        : "Pending"}
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                  <span>
                    Target: {p.target_date} · Confidence: {p.confidence_score}%
                  </span>
                  <span className="font-mono font-semibold">
                    {p.absolute_price_error !== null
                      ? `Abs Error: $${p.absolute_price_error.toFixed(2)} (${p.price_error_pct}%)`
                      : "Awaiting Verification"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <PredictionDetailModal prediction={selectedPred} onClose={() => setSelectedPred(null)} />
    </div>
  );
}

