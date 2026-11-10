import { useCallback, useEffect, useState } from "react";
import { Award, CheckCircle2, Clock, RefreshCw, ShieldCheck, Target, TrendingDown, TrendingUp, XCircle } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { StatCard } from "../components/StatCard";

export function AccountabilityPage() {
  const [data, setData] = useState(null);
  const [periodTab, setPeriodTab] = useState("weekly");
  const [dataSource, setDataSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [banner, setBanner] = useState("");

  const loadAccuracy = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getAccountabilityAccuracy({ data_source: dataSource });
      setData(res);
    } catch (err) {
      setBanner(err.message);
    } finally {
      setLoading(false);
    }
  }, [dataSource]);

  useEffect(() => {
    loadAccuracy();
  }, [loadAccuracy]);

  const handleRunDueVerification = async () => {
    setVerifying(true);
    setBanner("");
    try {
      const res = await api.verifyDuePredictions();
      setBanner(res.message);
      await loadAccuracy();
    } catch (err) {
      setBanner(err.message);
    } finally {
      setVerifying(false);
    }
  };

  const summary = data?.summary || {};
  const scoreDetails = data?.accountability_score_details || {};
  const stockWise = data?.stock_wise_accuracy || [];
  const bestStocks = data?.best_performing_stocks || [];
  const weakStocks = data?.weak_performing_stocks || [];
  const periodicData = periodTab === "weekly" ? data?.weekly_accuracy || [] : data?.monthly_accuracy || [];
  const perfOverTime = data?.performance_over_time || [];
  const scheduler = data?.scheduler || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-500">
            Prediction Accountability Dashboard
          </span>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Verified Accuracy, MAE & Accountability Score
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={dataSource}
            onChange={(e) => setDataSource(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
          >
            <option value="">All Data Sources</option>
            <option value="REAL_MARKET">Real Market Only</option>
            <option value="SIMULATED_TEST">Simulated Test Only</option>
          </select>
          <button
            onClick={loadAccuracy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            onClick={handleRunDueVerification}
            disabled={verifying}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            {verifying ? "Verifying..." : "Verify Due Predictions"}
          </button>
        </div>
      </div>

      {/* Transparency & Pending Exclusion Notice */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-500/25 bg-indigo-500/10 px-4 py-2.5 text-xs text-indigo-800 dark:text-indigo-200">
        <span>
          <strong>Formula Rule:</strong> Direction Accuracy = (Correct / Verified) × 100.{" "}
          {summary.pending_excluded_note || "Pending predictions are excluded from accuracy and MAE calculations."}
        </span>
        <span className="font-mono text-[11px] opacity-85">
          Scheduler: {scheduler.running ? `Active (${scheduler.interval_seconds}s)` : "On-Demand"}
        </span>
      </div>

      {banner && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
          {banner}
        </div>
      )}

      {/* 5 Core Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title="Total Predictions"
          value={summary.total_predictions ?? 0}
          subtitle={`${summary.verified_predictions ?? 0} verified`}
          icon={Target}
          accent="indigo"
        />
        <StatCard
          title="Correct"
          value={summary.correct_predictions ?? 0}
          subtitle="Direction matched actual"
          icon={CheckCircle2}
          accent="emerald"
        />
        <StatCard
          title="Incorrect"
          value={summary.incorrect_predictions ?? 0}
          subtitle="Direction missed actual"
          icon={XCircle}
          accent="rose"
        />
        <StatCard
          title="Pending"
          value={summary.pending_predictions ?? 0}
          subtitle="Excluded from accuracy"
          icon={Clock}
          accent="amber"
        />
        <StatCard
          title="Direction Accuracy"
          value={`${summary.direction_accuracy_pct ?? 0}%`}
          subtitle={`MAE: $${Number(summary.mean_absolute_error ?? 0).toFixed(2)}`}
          icon={Award}
          accent="sky"
        />
      </div>

      {/* Transparent Prediction Accountability Score Card */}
      <div className="fintech-card p-6">
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="flex flex-col justify-center rounded-2xl bg-gradient-to-br from-indigo-600/15 via-violet-500/10 to-transparent p-5 border border-indigo-500/20">
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-500">
              Prediction Accountability Score
            </p>
            <p className="mt-2 font-mono text-4xl font-extrabold text-slate-900 dark:text-white tabular-nums">
              {summary.accountability_score ?? 0} <span className="text-lg text-slate-400">/ 100</span>
            </p>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
              {scoreDetails.disclaimer}
            </p>
          </div>

          <div className="space-y-3 lg:col-span-2">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              How This Score Is Calculated (100% Transparent)
            </h3>
            <p className="font-mono text-xs text-slate-600 dark:text-slate-300">
              {scoreDetails.formula}
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
                <span className="text-slate-500">Direction Accuracy (60%)</span>
                <p className="mt-1 font-mono text-lg font-bold text-emerald-500">
                  {scoreDetails.components?.direction_accuracy_pct ?? 0}%
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
                <span className="text-slate-500">Price Precision (25%)</span>
                <p className="mt-1 font-mono text-lg font-bold text-indigo-500">
                  {scoreDetails.components?.price_precision_score ?? 0} / 100
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
                <span className="text-slate-500">Confidence Calibration (15%)</span>
                <p className="mt-1 font-mono text-lg font-bold text-sky-500">
                  {scoreDetails.components?.confidence_calibration_score ?? 0} / 100
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Best & Weak Performing Stocks */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="fintech-card p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <TrendingUp className="h-4 w-4 text-emerald-500" />
            Best-Performing Stocks
          </h3>
          {bestStocks.length === 0 ? (
            <p className="text-xs text-slate-500">No verified predictions yet.</p>
          ) : (
            <div className="space-y-2.5">
              {bestStocks.map((s) => (
                <div
                  key={s.symbol}
                  className="flex items-center justify-between rounded-xl bg-emerald-500/10 px-3.5 py-2.5 text-xs"
                >
                  <div>
                    <span className="font-bold text-slate-900 dark:text-white">{s.symbol}</span>
                    <span className="ml-2 text-slate-500">
                      ({s.correct}/{s.verified_predictions} verified)
                    </span>
                  </div>
                  <div className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {s.accuracy_pct}% · MAE ${s.mae.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="fintech-card p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <TrendingDown className="h-4 w-4 text-rose-500" />
            Weak-Performing Stocks (Needs Caution)
          </h3>
          {weakStocks.length === 0 ? (
            <p className="text-xs text-slate-500">No verified predictions yet.</p>
          ) : (
            <div className="space-y-2.5">
              {weakStocks.map((s) => (
                <div
                  key={s.symbol}
                  className="flex items-center justify-between rounded-xl bg-rose-500/10 px-3.5 py-2.5 text-xs"
                >
                  <div>
                    <span className="font-bold text-slate-900 dark:text-white">{s.symbol}</span>
                    <span className="ml-2 text-slate-500">
                      ({s.correct}/{s.verified_predictions} verified)
                    </span>
                  </div>
                  <div className="font-mono font-bold text-rose-600 dark:text-rose-400">
                    {s.accuracy_pct}% · MAE ${s.mae.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Charts: Performance Over Time & Stock-wise Accuracy */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="fintech-card p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            Prediction Performance Over Time
          </h3>
          <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
            Cumulative & daily verified direction accuracy (%)
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={perfOverTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={36} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.94)",
                    borderRadius: "10px",
                    fontSize: "12px",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="cumulative_accuracy_pct"
                  name="Cumulative Accuracy %"
                  stroke="#6366f1"
                  strokeWidth={2.5}
                />
                <Line
                  type="monotone"
                  dataKey="daily_accuracy_pct"
                  name="Daily Accuracy %"
                  stroke="#10b981"
                  strokeDasharray="4 4"
                  strokeWidth={1.6}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="fintech-card p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            Stock-Wise Direction Accuracy (%)
          </h3>
          <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
            Comparing model reliability across tracked equities
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stockWise}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                <XAxis dataKey="symbol" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={36} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.94)",
                    borderRadius: "10px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="accuracy_pct" name="Accuracy %" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Weekly & Monthly Accuracy Reports */}
      <div className="fintech-card p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Weekly & Monthly Accuracy Breakdown
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Verified predictions grouped by calendar week or month
            </p>
          </div>

          <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
            <button
              onClick={() => setPeriodTab("weekly")}
              className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                periodTab === "weekly"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                  : "text-slate-500"
              }`}
            >
              Weekly Accuracy
            </button>
            <button
              onClick={() => setPeriodTab("monthly")}
              className={`rounded-lg px-3 py-1 text-xs font-semibold ${
                periodTab === "monthly"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                  : "text-slate-500"
              }`}
            >
              Monthly Accuracy
            </button>
          </div>
        </div>

        {loading && !data ? (
          <div className="py-8 text-center text-xs text-slate-500">Loading accountability metrics...</div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={periodicData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={35} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15, 23, 42, 0.94)",
                      borderRadius: "10px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="accuracy_pct" name="Accuracy %" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="py-2 font-medium">Period</th>
                    <th className="py-2 font-medium">Verified</th>
                    <th className="py-2 font-medium">Correct / Wrong</th>
                    <th className="py-2 font-medium">Accuracy %</th>
                    <th className="py-2 font-medium">MAE ($)</th>
                    <th className="py-2 font-medium">Top Stock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
                  {periodicData.map((r) => (
                    <tr key={r.period}>
                      <td className="py-2.5 font-semibold text-slate-900 dark:text-white">{r.period}</td>
                      <td className="py-2.5">{r.verified_predictions}</td>
                      <td className="py-2.5">
                        <span className="font-semibold text-emerald-500">{r.correct}</span> /{" "}
                        <span className="font-semibold text-rose-500">{r.incorrect}</span>
                      </td>
                      <td className="py-2.5 font-bold text-indigo-500">{r.accuracy_pct}%</td>
                      <td className="py-2.5 font-mono">${r.mae.toFixed(2)}</td>
                      <td className="py-2.5 font-semibold">{r.top_performing_symbol}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
