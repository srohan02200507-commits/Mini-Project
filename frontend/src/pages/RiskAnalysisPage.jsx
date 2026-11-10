import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, BookOpen, ShieldCheck, TrendingDown } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { RiskBadge } from "../components/SignalBadge";
import { SimulatedBanner } from "../components/SimulatedBanner";
import { StatCard } from "../components/StatCard";

export function RiskAnalysisPage() {
  const [symbol, setSymbol] = useState("NVDA");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadRisk = useCallback(async (sym) => {
    setLoading(true);
    try {
      const res = await api.getRiskOverview(sym);
      setData(res);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRisk(symbol);
  }, [symbol, loadRisk]);

  const stockRisk = data?.selected_stock_risk;
  const portRisk = data?.portfolio_risk;
  const allRisks = data?.all_stocks_risk || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Risk Analysis & Volatility Insights
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Historical volatility, drawdown stress, 95% daily VaR, and virtual portfolio concentration checks
          </p>
        </div>

        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
        >
          {allRisks.map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.symbol} — {s.risk_level} Risk
            </option>
          ))}
        </select>
      </div>

      <SimulatedBanner extraText="TradeWise AI never guarantees profits or returns. Risk indicators reflect simulated historical dispersion and can change suddenly." />

      {loading && !data ? (
        <div className="py-12 text-center text-xs text-slate-500">Analyzing risk metrics...</div>
      ) : (
        <>
          {stockRisk && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  title={`${stockRisk.symbol} Annualized Volatility`}
                  value={`${stockRisk.annualized_volatility_pct}%`}
                  subtitle={`30D rolling: ${stockRisk.recent_30d_volatility_pct}%`}
                  icon={Activity}
                  accent="amber"
                />
                <StatCard
                  title="95% Daily Value at Risk"
                  value={`-${stockRisk.value_at_risk_95_pct}%`}
                  subtitle="5th percentile historical daily loss"
                  icon={AlertTriangle}
                  accent="rose"
                />
                <StatCard
                  title="Maximum Drawdown"
                  value={`${stockRisk.max_drawdown_pct}%`}
                  subtitle={`Beta vs SPY: ${stockRisk.beta_vs_spy}`}
                  icon={TrendingDown}
                  accent="rose"
                />
                <StatCard
                  title="Portfolio Diversification"
                  value={`${portRisk?.diversification_score ?? 100} / 100`}
                  subtitle={`Cash buffer: ${portRisk?.cash_buffer_pct ?? 100}%`}
                  icon={ShieldCheck}
                  accent="emerald"
                />
              </div>

              {/* Charts: Rolling Volatility & Historical Drawdown */}
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="fintech-card p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                        60-Day Rolling Annualized Volatility — {stockRisk.symbol}
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Measures simulated price turbulence over time
                      </p>
                    </div>
                    <RiskBadge level={stockRisk.risk_level} />
                  </div>
                  <div className="h-60">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={stockRisk.series}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                        <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `${v}%`} width={42} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "rgba(15, 23, 42, 0.94)",
                            borderRadius: "10px",
                            fontSize: "12px",
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="volatility_pct"
                          name="Annualized Volatility %"
                          stroke="#f59e0b"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="fintech-card p-5">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                    60-Day Drawdown Profile — {stockRisk.symbol}
                  </h3>
                  <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
                    Percentage distance below prior simulated peak price
                  </p>
                  <div className="h-60">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={stockRisk.series}>
                        <defs>
                          <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.35} />
                            <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                        <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => `${v}%`} width={42} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "rgba(15, 23, 42, 0.94)",
                            borderRadius: "10px",
                            fontSize: "12px",
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="drawdown_pct"
                          name="Drawdown %"
                          stroke="#f43f5e"
                          fill="url(#ddGrad)"
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Portfolio Risk Warnings + Educational Explanations */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="fintech-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
                Your Virtual Portfolio Risk Check
              </h3>
              <div className="mb-3 grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
                  <span className="text-slate-500">Weighted Volatility</span>
                  <p className="mt-1 font-mono text-base font-bold">{portRisk?.weighted_volatility_pct ?? 0}%</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
                  <span className="text-slate-500">Largest Position Share</span>
                  <p className="mt-1 font-mono text-base font-bold">
                    {portRisk?.largest_position_pct ?? 0}%{" "}
                    {portRisk?.largest_position_symbol ? `(${portRisk.largest_position_symbol})` : ""}
                  </p>
                </div>
              </div>
              <ul className="space-y-2">
                {(portRisk?.warnings || []).map((w, i) => (
                  <li
                    key={i}
                    className="rounded-xl border border-slate-200/80 bg-slate-50/70 px-3 py-2 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-300"
                  >
                    {w}
                  </li>
                ))}
              </ul>
            </div>

            <div className="fintech-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                <BookOpen className="h-4 w-4 text-indigo-500" />
                Educational Risk Glossary
              </h3>
              <div className="space-y-2.5">
                {(data?.educational_guides || []).map((g) => (
                  <div key={g.title} className="rounded-xl border border-slate-200/80 p-3 dark:border-slate-800">
                    <p className="text-xs font-bold text-slate-900 dark:text-white">{g.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                      {g.explanation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* All Stocks Risk Matrix */}
          <div className="fintech-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
              Cross-Market Simulated Risk Comparison
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="py-2 font-medium">Stock</th>
                    <th className="py-2 font-medium">Sector</th>
                    <th className="py-2 font-medium">Annual Vol</th>
                    <th className="py-2 font-medium">95% Daily VaR</th>
                    <th className="py-2 font-medium">Max Drawdown</th>
                    <th className="py-2 font-medium">Beta (SPY)</th>
                    <th className="py-2 font-medium">Risk Rating</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
                  {allRisks.map((r) => (
                    <tr
                      key={r.symbol}
                      onClick={() => setSymbol(r.symbol)}
                      className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40"
                    >
                      <td className="py-2.5 font-semibold text-indigo-600 dark:text-indigo-400">{r.symbol}</td>
                      <td className="py-2.5 text-slate-500">{r.sector}</td>
                      <td className="py-2.5 font-mono">{r.annualized_volatility_pct}%</td>
                      <td className="py-2.5 font-mono text-rose-500">-{r.value_at_risk_95_pct}%</td>
                      <td className="py-2.5 font-mono text-rose-500">{r.max_drawdown_pct}%</td>
                      <td className="py-2.5 font-mono">{r.beta_vs_spy}</td>
                      <td className="py-2.5">
                        <RiskBadge level={r.risk_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

