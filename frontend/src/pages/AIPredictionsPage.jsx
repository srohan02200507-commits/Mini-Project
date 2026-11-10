import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  ExternalLink,
  Layers,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { api } from "../api/client";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "../components/SignalBadge";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "SPY"];

export function AIPredictionsPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [customSymbol, setCustomSymbol] = useState("");
  const [dataSource, setDataSource] = useState("REAL_MARKET");
  const [horizonMode, setHorizonMode] = useState("1D");
  const [tolerancePct, setTolerancePct] = useState("0.50");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [latestPrediction, setLatestPrediction] = useState(null);
  const [recentList, setRecentList] = useState([]);

  const loadRecent = useCallback(async () => {
    try {
      const res = await api.getPredictions({ limit: 8 });
      setRecentList(res.predictions || []);
      if (!latestPrediction && res.predictions?.length) {
        setLatestPrediction(res.predictions[0]);
      }
    } catch {
      // Ignore initial load error
    }
  }, [latestPrediction]);

  useEffect(() => {
    loadRecent();
  }, [loadRecent]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError("");
    setStatusMsg("");
    setSubmitting(true);

    const activeSymbol = (customSymbol.trim() || symbol).toUpperCase();
    const payload = {
      stock_symbol: activeSymbol,
      data_source: dataSource,
      tolerance_pct: Number(tolerancePct),
    };

    if (horizonMode === "1H") {
      payload.horizon_hours = 1;
      payload.horizon_days = 1;
    } else if (horizonMode === "4H") {
      payload.horizon_hours = 4;
      payload.horizon_days = 1;
    } else {
      payload.horizon_days = Number(horizonMode.replace("D", "")) || 1;
    }

    try {
      const res = await api.createPrediction(payload);
      setLatestPrediction(res.prediction);
      setStatusMsg(res.message);
      const listRes = await api.getPredictions({ limit: 8 });
      setRecentList(listRes.predictions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            AI Predictions Studio
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Generate immutable UP / DOWN / SIDEWAYS predictions powered by Scikit-learn & permanently log them for verification.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/history"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          >
            View Full History
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Generator Form */}
        <form onSubmit={handleGenerate} className="fintech-card space-y-4 p-5">
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-indigo-500" />
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Generate & Record Forecast
            </h3>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Market Data Provider
            </label>
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
              <button
                type="button"
                onClick={() => setDataSource("REAL_MARKET")}
                className={`rounded-lg py-2 text-xs font-semibold transition ${
                  dataSource === "REAL_MARKET"
                    ? "bg-white text-emerald-600 shadow-sm dark:bg-slate-900 dark:text-emerald-400"
                    : "text-slate-500"
                }`}
              >
                Real Market Data
              </button>
              <button
                type="button"
                onClick={() => setDataSource("SIMULATED_TEST")}
                className={`rounded-lg py-2 text-xs font-semibold transition ${
                  dataSource === "SIMULATED_TEST"
                    ? "bg-white text-amber-600 shadow-sm dark:bg-slate-900 dark:text-amber-400"
                    : "text-slate-500"
                }`}
              >
                Simulated Test Feed
              </button>
            </div>
            <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
              {dataSource === "REAL_MARKET"
                ? "Fetches live Yahoo Finance historical OHLCV. Never invents prices if unreachable."
                : "Uses isolated local simulated stocks for offline classroom testing."}
            </p>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
              Select Stock Symbol
            </label>
            <div className="flex flex-wrap gap-1.5">
              {DEFAULT_SYMBOLS.map((sym) => (
                <button
                  key={sym}
                  type="button"
                  onClick={() => {
                    setSymbol(sym);
                    setCustomSymbol("");
                  }}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                    !customSymbol && symbol === sym
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  {sym}
                </button>
              ))}
            </div>
            {dataSource === "REAL_MARKET" && (
              <input
                type="text"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
                placeholder="Or enter any real ticker (e.g., NFLX, AMD)"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
              />
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Target Horizon
              </label>
              <select
                value={horizonMode}
                onChange={(e) => setHorizonMode(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="1H">1 Hour Ahead</option>
                <option value="4H">4 Hours Ahead</option>
                <option value="1D">1 Trading Day</option>
                <option value="3D">3 Trading Days</option>
                <option value="5D">5 Trading Days</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Sideways Tolerance
              </label>
              <select
                value={tolerancePct}
                onChange={(e) => setTolerancePct(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="0.25">±0.25% Strict</option>
                <option value="0.50">±0.50% Standard</option>
                <option value="1.00">±1.00% Wide</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-500">
              {error}
            </div>
          )}
          {statusMsg && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600 dark:text-emerald-300">
              {statusMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white shadow-sm shadow-indigo-600/25 hover:bg-indigo-500 disabled:opacity-60"
          >
            <Sparkles className="h-4 w-4" />
            {submitting ? "Training & Recording..." : "Generate & Save Prediction"}
          </button>

          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Assigns a unique Prediction ID and appends permanently to the Accountability Engine.
          </p>
        </form>

        {/* Right: Complete 4-Part Prediction Explanation */}
        <div className="space-y-4 lg:col-span-2">
          {latestPrediction ? (
            <div className="fintech-card p-6">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4 dark:border-slate-800">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-500">
                      {latestPrediction.prediction_id}
                    </span>
                    <DataSourceBadge
                      dataSource={latestPrediction.data_source}
                      isSimulated={latestPrediction.is_simulated}
                    />
                    <ResultBadge
                      status={latestPrediction.verification_status}
                      result={latestPrediction.prediction_result}
                    />
                  </div>
                  <h3 className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                    {latestPrediction.stock_symbol} — {latestPrediction.stock_name}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Model: {latestPrediction.model_name} ({latestPrediction.model_version}) · Target:{" "}
                    {latestPrediction.target_timestamp?.replace("T", " ").slice(0, 16)} UTC
                  </p>
                </div>

                <div className="text-right">
                  <DirectionBadge direction={latestPrediction.predicted_direction} />
                  <p className="mt-1 font-mono text-xl font-bold text-slate-900 dark:text-white tabular-nums">
                    ${latestPrediction.predicted_price.toFixed(2)}
                  </p>
                  <p className="text-xs text-slate-500 tabular-nums">
                    from ${latestPrediction.starting_price.toFixed(2)} (
                    {latestPrediction.predicted_return_pct >= 0 ? "+" : ""}
                    {latestPrediction.predicted_return_pct}%) · Conf:{" "}
                    <span className="font-bold text-indigo-500">
                      {latestPrediction.confidence_score}%
                    </span>
                  </p>
                </div>
              </div>

              <div className="mt-4 space-y-4">
                <div className="rounded-xl bg-indigo-500/5 p-4 border border-indigo-500/20">
                  <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-500">
                    <CheckCircle2 className="h-4 w-4" />
                    Why AI Predicted {latestPrediction.predicted_direction}
                  </h4>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-700 dark:text-slate-200">
                    {latestPrediction.prediction_reason}
                  </p>
                </div>

                <div>
                  <h4 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    <Layers className="h-4 w-4 text-sky-500" />
                    Historical Price Patterns Influencing Forecast
                  </h4>
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    {(latestPrediction.historical_patterns || []).map((pat, i) => (
                      <div key={i} className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {pat.pattern}
                          </span>
                          <span className="font-mono text-[11px] font-bold text-indigo-500">
                            {pat.metric} ({pat.signal})
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                          {pat.detail}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200/80 p-3.5 dark:border-slate-800">
                    <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                      <Clock className="h-4 w-4 text-emerald-500" />
                      What Confidence ({latestPrediction.confidence_score}%) Means
                    </h4>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                      {latestPrediction.confidence_meaning}
                    </p>
                  </div>

                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5">
                    <h4 className="flex items-center gap-1.5 text-xs font-bold text-amber-600 dark:text-amber-400">
                      <AlertTriangle className="h-4 w-4" />
                      Factors That Could Make It Inaccurate
                    </h4>
                    <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs text-slate-600 dark:text-slate-300">
                      {(latestPrediction.invalidation_factors || []).map((f, idx) => (
                        <li key={idx}>{f}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="fintech-card flex h-72 items-center justify-center p-6 text-sm text-slate-500">
              Select a stock and click "Generate & Save Prediction" to inspect the full AI rationale.
            </div>
          )}
        </div>
      </div>

      {/* Recent Immutable Log */}
      <div className="fintech-card p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Recently Recorded Predictions (Click to Inspect)
            </h3>
          </div>
          <Link to="/comparison" className="text-xs font-semibold text-indigo-500 hover:text-indigo-400">
            Compare Visually →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="py-2 font-medium">Prediction ID</th>
                <th className="py-2 font-medium">Stock</th>
                <th className="py-2 font-medium">Source</th>
                <th className="py-2 font-medium">Start → Predicted</th>
                <th className="py-2 font-medium">Direction</th>
                <th className="py-2 font-medium">Confidence</th>
                <th className="py-2 font-medium">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
              {recentList.map((p) => (
                <tr
                  key={p.prediction_id}
                  onClick={() => setLatestPrediction(p)}
                  className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40"
                >
                  <td className="py-2.5 font-mono font-semibold text-indigo-500">{p.prediction_id}</td>
                  <td className="py-2.5 font-semibold text-slate-900 dark:text-white">{p.stock_symbol}</td>
                  <td className="py-2.5">
                    <DataSourceBadge dataSource={p.data_source} isSimulated={p.is_simulated} />
                  </td>
                  <td className="py-2.5 font-mono">
                    ${p.starting_price.toFixed(2)} → ${p.predicted_price.toFixed(2)}
                  </td>
                  <td className="py-2.5">
                    <DirectionBadge direction={p.predicted_direction} />
                  </td>
                  <td className="py-2.5 font-mono">{p.confidence_score}%</td>
                  <td className="py-2.5">
                    <ResultBadge status={p.verification_status} result={p.prediction_result} />
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

