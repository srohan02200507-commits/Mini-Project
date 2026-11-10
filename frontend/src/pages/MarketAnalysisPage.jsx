import { useCallback, useEffect, useState } from "react";
import { Cpu, Radio, RefreshCw, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { PriceChart } from "../components/PriceChart";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "../components/SignalBadge";
import { SimulatedBanner } from "../components/SimulatedBanner";

const REAL_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "SPY"];

export function MarketAnalysisPage() {
  const [dataSource, setDataSource] = useState("REAL_MARKET");
  const [stocks, setStocks] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [customTicker, setCustomTicker] = useState("");
  const [daysRange, setDaysRange] = useState(90);
  const [detail, setDetail] = useState(null);
  const [liveIntraday, setLiveIntraday] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [horizonDays, setHorizonDays] = useState(1);
  const [statusMsg, setStatusMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [showBands, setShowBands] = useState(true);

  const loadStocks = useCallback(async () => {
    try {
      const res = await api.getStocks(dataSource);
      setStocks(res.stocks || []);
    } catch {
      setStocks([]);
    }
  }, [dataSource]);

  const loadDetail = useCallback(async (sym, days, source) => {
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await api.getStockDetail(sym, days, source);
      setDetail(res);
      if (source === "REAL_MARKET") {
        try {
          const q = await api.getLiveQuote(sym, true);
          setLiveIntraday(q.intraday || []);
        } catch {
          setLiveIntraday([]);
        }
      } else {
        setLiveIntraday([]);
      }
    } catch (err) {
      setErrorMsg(err.message);
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStocks();
  }, [loadStocks]);

  useEffect(() => {
    loadDetail(selectedSymbol, daysRange, dataSource);
  }, [selectedSymbol, daysRange, dataSource, loadDetail]);

  const handleGeneratePrediction = async () => {
    setGenerating(true);
    setStatusMsg("");
    setErrorMsg("");
    try {
      const res = await api.createPrediction({
        stock_symbol: selectedSymbol,
        data_source: dataSource,
        horizon_days: horizonDays,
      });
      setStatusMsg(res.message);
      await loadDetail(selectedSymbol, daysRange, dataSource);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const stock = detail?.stock;
  const indicators = detail?.indicators || {};
  const prediction = detail?.latest_prediction;
  const history = detail?.history || [];
  const tickerList = stocks.length > 0 ? stocks.map((s) => s.symbol) : REAL_TICKERS;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Live Stock Analysis & Technical Indicators
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Analyze real-time market candles or switch to isolated Simulated Test Mode
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800">
          <button
            onClick={() => setDataSource("REAL_MARKET")}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              dataSource === "REAL_MARKET"
                ? "bg-white text-emerald-600 shadow-sm dark:bg-slate-900 dark:text-emerald-400"
                : "text-slate-500"
            }`}
          >
            <Radio className="h-3.5 w-3.5" />
            Real Market Data
          </button>
          <button
            onClick={() => setDataSource("SIMULATED_TEST")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              dataSource === "SIMULATED_TEST"
                ? "bg-white text-amber-600 shadow-sm dark:bg-slate-900 dark:text-amber-400"
                : "text-slate-500"
            }`}
          >
            Simulated Test Feed
          </button>
        </div>
      </div>

      {dataSource === "SIMULATED_TEST" && <SimulatedBanner />}

      {/* Ticker strip + custom real symbol lookup */}
      <div className="flex flex-wrap items-center gap-2">
        {tickerList.map((sym) => {
          const quote = stocks.find((s) => s.symbol === sym);
          return (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
                selectedSymbol === sym
                  ? "border-indigo-500 bg-indigo-600 text-white"
                  : "border-slate-200 bg-white text-slate-700 hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
              }`}
            >
              <span>{sym}</span>
              {quote && (
                <>
                  <span className="font-mono opacity-85">${quote.current_price.toFixed(2)}</span>
                  <span
                    className={
                      selectedSymbol === sym
                        ? "text-white/90"
                        : quote.day_change_pct >= 0
                        ? "text-emerald-500"
                        : "text-rose-500"
                    }
                  >
                    {quote.day_change_pct >= 0 ? `+${quote.day_change_pct}%` : `${quote.day_change_pct}%`}
                  </span>
                </>
              )}
            </button>
          );
        })}

        {dataSource === "REAL_MARKET" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (customTicker.trim()) {
                setSelectedSymbol(customTicker.trim().toUpperCase());
                setCustomTicker("");
              }
            }}
            className="flex items-center gap-1.5"
          >
            <input
              type="text"
              value={customTicker}
              onChange={(e) => setCustomTicker(e.target.value.toUpperCase())}
              placeholder="Any ticker (e.g. AMD)"
              className="w-36 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900"
            />
            <button
              type="submit"
              className="rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
            >
              Load
            </button>
          </form>
        )}
      </div>

      {errorMsg && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs text-rose-500">
          {errorMsg}
        </div>
      )}
      {statusMsg && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-600 dark:text-emerald-300">
          {statusMsg}
        </div>
      )}

      {stock && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <div className="fintech-card p-5">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">{stock.symbol}</h3>
                    <DataSourceBadge dataSource={stock.data_source} isSimulated={stock.is_simulated} />
                    <button
                      onClick={() => loadDetail(selectedSymbol, daysRange, dataSource)}
                      className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                      title="Refresh quote"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{stock.name}</p>
                </div>

                <div className="text-right">
                  <p className="font-mono text-2xl font-bold text-slate-900 dark:text-white tabular-nums">
                    ${stock.current_price.toFixed(2)}
                  </p>
                  <p
                    className={`inline-flex items-center gap-1 text-xs font-semibold tabular-nums ${
                      stock.day_change_pct >= 0 ? "text-emerald-500" : "text-rose-500"
                    }`}
                  >
                    {stock.day_change_pct >= 0 ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                    {stock.day_change_pct >= 0 ? `+${stock.day_change_pct}%` : `${stock.day_change_pct}%`}
                  </p>
                </div>
              </div>

              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex gap-1.5">
                  {[30, 60, 90, 150].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDaysRange(d)}
                      className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                        daysRange === d
                          ? "bg-indigo-600 text-white"
                          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      }`}
                    >
                      {d}D
                    </button>
                  ))}
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={showBands}
                    onChange={(e) => setShowBands(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600"
                  />
                  Show Bollinger Bands
                </label>
              </div>

              {loading ? (
                <div className="flex h-72 items-center justify-center text-xs text-slate-500">Loading chart...</div>
              ) : (
                <PriceChart data={history} showSma showBands={showBands} height={310} />
              )}
            </div>

            {/* Live Intraday 5m chart when in REAL_MARKET mode + RSI */}
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="fintech-card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  {liveIntraday.length > 0 ? "Live 5-Minute Intraday Feed" : "RSI (14-Day Momentum)"}
                </h3>
                <div className="mt-3 h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    {liveIntraday.length > 0 ? (
                      <LineChart data={liveIntraday}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" vertical={false} />
                        <XAxis dataKey="time_label" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={20} />
                        <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={48} tickFormatter={(v) => `$${v}`} />
                        <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.94)", borderRadius: "10px", fontSize: "12px" }} />
                        <Line type="monotone" dataKey="close" name="Live Intraday ($)" stroke="#10b981" dot={false} strokeWidth={2} />
                      </LineChart>
                    ) : (
                      <LineChart data={history}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" vertical={false} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} width={30} />
                        <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.94)", borderRadius: "10px", fontSize: "12px" }} />
                        <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="3 3" />
                        <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
                        <Line type="monotone" dataKey="rsi_14" name="RSI 14" stroke="#a855f7" dot={false} strokeWidth={1.8} />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="fintech-card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Trading Volume (Last 30 Bars)
                </h3>
                <div className="mt-3 h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={history.slice(-30)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={42} tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`} />
                      <Tooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.94)", borderRadius: "10px", fontSize: "12px" }} />
                      <Bar dataKey="volume" name="Volume" fill="#38bdf8" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Run Prediction & Indicators */}
          <div className="space-y-6">
            <div className="fintech-card p-5">
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Record AI Prediction
                </h3>
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Trains Scikit-learn ensemble on {selectedSymbol} ({dataSource}) and records an immutable forecast.
              </p>

              <div className="mt-4 flex items-center gap-2">
                <select
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(Number(e.target.value))}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium dark:border-slate-700 dark:bg-slate-800"
                >
                  <option value={1}>1 Trading Day</option>
                  <option value={3}>3 Trading Days</option>
                  <option value={5}>5 Trading Days</option>
                </select>
                <button
                  onClick={handleGeneratePrediction}
                  disabled={generating}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {generating ? "Generating..." : "Predict & Save"}
                </button>
              </div>
            </div>

            {prediction && (
              <div className="fintech-card p-5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-indigo-500">{prediction.prediction_id}</span>
                  <DirectionBadge direction={prediction.predicted_direction} />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
                  <div>
                    <p className="text-[11px] text-slate-500">Predicted Price</p>
                    <p className="font-mono text-lg font-bold">${prediction.predicted_price.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500">Confidence</p>
                    <p className="font-mono text-lg font-bold text-indigo-500">{prediction.confidence_score}%</p>
                  </div>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                  {prediction.prediction_reason}
                </p>
                <div className="mt-3">
                  <ResultBadge status={prediction.verification_status} result={prediction.prediction_result} />
                </div>
              </div>
            )}

            <div className="fintech-card p-5">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Technical Readings
              </h3>
              <dl className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-slate-800/50">
                  <dt className="text-slate-500">RSI (14)</dt>
                  <dd className="mt-0.5 font-mono font-semibold">{indicators.rsi_14 ?? "—"}</dd>
                </div>
                <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-slate-800/50">
                  <dt className="text-slate-500">SMA 5 / SMA 20</dt>
                  <dd className="mt-0.5 font-mono font-semibold">${indicators.sma_5 ?? "—"} / ${indicators.sma_20 ?? "—"}</dd>
                </div>
                <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-slate-800/50">
                  <dt className="text-slate-500">5D Return</dt>
                  <dd className="mt-0.5 font-mono font-semibold">{indicators.return_5d_pct ?? "—"}%</dd>
                </div>
                <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-slate-800/50">
                  <dt className="text-slate-500">20D Volatility</dt>
                  <dd className="mt-0.5 font-mono font-semibold">{indicators.volatility_20 ?? "—"}%</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
