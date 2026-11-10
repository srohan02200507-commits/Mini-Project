import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Award,
  CheckCircle2,
  Clock,
  Cpu,
  Radio,
  RefreshCw,
  ShieldCheck,
  Target,
  Wallet,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { PredictionDetailModal } from "../components/PredictionDetailModal";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "../components/SignalBadge";
import { StatCard } from "../components/StatCard";

export function DashboardPage() {
  const [accuracyData, setAccuracyData] = useState(null);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [liveQuotes, setLiveQuotes] = useState([]);
  const [selectedPred, setSelectedPred] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [banner, setBanner] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [accRes, histRes, portRes] = await Promise.all([
        api.getAccountabilityAccuracy(),
        api.getPredictionHistory({ limit: 8 }),
        api.getPortfolio(false),
      ]);
      setAccuracyData(accRes);
      setRecentPredictions(histRes.history || []);
      setPortfolio(portRes);

      try {
        const liveRes = await api.getLiveQuotes("AAPL,MSFT,NVDA,TSLA,SPY");
        setLiveQuotes(liveRes.quotes || []);
      } catch {
        setLiveQuotes([]);
      }
    } catch (err) {
      setBanner(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleVerifyDue = async () => {
    setVerifying(true);
    setBanner("");
    try {
      const res = await api.verifyDuePredictions();
      setBanner(res.message);
      await loadDashboard();
    } catch (err) {
      setBanner(err.message);
    } finally {
      setVerifying(false);
    }
  };

  const summary = accuracyData?.summary || {};
  const perfSeries = accuracyData?.performance_over_time || [];

  if (loading && !accuracyData) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        Loading Prediction Accountability Dashboard...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500">
            TradeWise AI — Prediction Accountability Core
          </p>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Accountability & Market Command Center
          </h2>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            to="/predictions"
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            <Cpu className="h-3.5 w-3.5" />
            New AI Prediction
          </Link>
          <button
            onClick={handleVerifyDue}
            disabled={verifying}
            className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-3.5 py-2 text-xs font-semibold text-indigo-600 hover:bg-indigo-500/20 dark:text-indigo-300"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            {verifying ? "Verifying..." : "Verify Due Predictions"}
          </button>
          <button
            onClick={loadDashboard}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Live Real-Time Market Strip */}
      {liveQuotes.length > 0 && (
        <div className="fintech-card p-3.5">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-500">
              <Radio className="h-3.5 w-3.5 animate-pulse" />
              Live Real-Time Market Quotes
            </span>
            <Link to="/trading" className="font-semibold text-indigo-500 hover:text-indigo-400">
              Open Real-Time Virtual Trading →
            </Link>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-5">
            {liveQuotes.map((q) => (
              <div key={q.symbol} className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-900 dark:text-white">{q.symbol}</span>
                  <span className={`font-mono font-semibold ${q.day_change_pct >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                    {q.day_change_pct >= 0 ? "+" : ""}
                    {q.day_change_pct}%
                  </span>
                </div>
                <p className="mt-0.5 font-mono text-sm font-bold tabular-nums">${q.current_price.toFixed(2)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {banner && (
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
          {banner}
        </div>
      )}

      {/* Accountability KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Accountability Score"
          value={`${summary.accountability_score ?? 0} / 100`}
          subtitle={`Direction Accuracy: ${summary.direction_accuracy_pct ?? 0}%`}
          icon={Award}
          accent="indigo"
        />
        <StatCard
          title="Verified Outcomes"
          value={`${summary.correct_predictions ?? 0} / ${summary.verified_predictions ?? 0}`}
          subtitle={`${summary.incorrect_predictions ?? 0} incorrect · ${summary.pending_predictions ?? 0} pending`}
          icon={CheckCircle2}
          accent="emerald"
        />
        <StatCard
          title="Mean Absolute Error"
          value={`$${Number(summary.mean_absolute_error ?? 0).toFixed(2)}`}
          subtitle={`Avg ${summary.mean_absolute_pct_error ?? 0}% MAPE (excl. pending)`}
          icon={Target}
          accent="amber"
        />
        <StatCard
          title="Virtual Portfolio Equity"
          value={`$${Number(portfolio?.total_equity ?? 100000).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          trend={portfolio?.total_return_pct ?? 0}
          subtitle="Paper-trading funds only"
          icon={Wallet}
          accent="sky"
        />
      </div>

      {/* Accuracy Over Time + Direction Breakdown */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="fintech-card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Cumulative Prediction Accuracy Over Time
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Tracks historical verified accuracy (%) chronologically without deleting past errors
              </p>
            </div>
            <Link to="/accountability" className="text-xs font-semibold text-indigo-500 hover:text-indigo-400">
              Full Analytics →
            </Link>
          </div>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={perfSeries}>
                <defs>
                  <linearGradient id="dashAcc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={35} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.94)",
                    borderRadius: "10px",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="cumulative_accuracy_pct"
                  name="Cumulative Accuracy %"
                  stroke="#6366f1"
                  strokeWidth={2.2}
                  fill="url(#dashAcc)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="fintech-card flex flex-col justify-between p-5">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Direction Accuracy (UP / DOWN / SIDEWAYS)
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Pending predictions are strictly excluded
            </p>
            <div className="mt-4 space-y-3">
              {["UP", "DOWN", "SIDEWAYS"].map((dir) => {
                const info = accuracyData?.direction_breakdown?.[dir] || {
                  verified: 0,
                  correct: 0,
                  accuracy_pct: 0,
                };
                return (
                  <div key={dir} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                    <div className="flex items-center justify-between">
                      <DirectionBadge direction={dir} />
                      <span className="font-mono text-xs font-bold">{info.accuracy_pct}%</span>
                    </div>
                    <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                      {info.correct} correct out of {info.verified} verified
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2 rounded-xl bg-amber-500/10 p-2.5 text-[11px] text-amber-700 dark:text-amber-300">
            <Clock className="h-4 w-4 shrink-0" />
            <span>{summary.pending_predictions ?? 0} prediction(s) currently PENDING VERIFICATION.</span>
          </div>
        </div>
      </div>

      {/* Recent Immutable Predictions Table */}
      <div className="fintech-card p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Recent Recorded Predictions
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Click any prediction to inspect full explanation, historical patterns, and verification details
            </p>
          </div>
          <Link to="/history" className="text-xs font-semibold text-indigo-500 hover:text-indigo-400">
            Open Full Prediction History →
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
                <th className="py-2 font-medium">Actual</th>
                <th className="py-2 font-medium">Predicted Dir</th>
                <th className="py-2 font-medium">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
              {recentPredictions.map((p) => (
                <tr
                  key={p.prediction_id}
                  onClick={() => setSelectedPred(p)}
                  className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40"
                >
                  <td className="py-2.5 font-mono font-semibold text-indigo-500">{p.prediction_id}</td>
                  <td className="py-2.5 font-bold text-slate-900 dark:text-white">{p.stock_symbol}</td>
                  <td className="py-2.5">
                    <DataSourceBadge dataSource={p.data_source} isSimulated={p.is_simulated} />
                  </td>
                  <td className="py-2.5 font-mono">
                    ${p.starting_price.toFixed(2)} → ${p.predicted_price.toFixed(2)}
                  </td>
                  <td className="py-2.5 font-mono">
                    {p.actual_price !== null ? `$${p.actual_price.toFixed(2)}` : "—"}
                  </td>
                  <td className="py-2.5">
                    <DirectionBadge direction={p.predicted_direction} />
                  </td>
                  <td className="py-2.5">
                    <ResultBadge status={p.verification_status} result={p.prediction_result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <PredictionDetailModal prediction={selectedPred} onClose={() => setSelectedPred(null)} />
    </div>
  );
}
