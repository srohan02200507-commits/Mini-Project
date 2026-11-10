import { useCallback, useEffect, useState } from "react";
import { CheckCircle, Eye, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import { PredictionDetailModal } from "../components/PredictionDetailModal";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "../components/SignalBadge";

export function PredictionHistoryPage() {
  const [history, setHistory] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedPred, setSelectedPred] = useState(null);
  const [verifyingId, setVerifyingId] = useState("");
  const [banner, setBanner] = useState("");
  const [filters, setFilters] = useState({
    search: "",
    date: "",
    direction: "",
    result: "",
    data_source: "",
  });

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getPredictionHistory({
        search: filters.search,
        date: filters.date,
        direction: filters.direction,
        result: filters.result,
        data_source: filters.data_source,
        limit: 200,
      });
      setHistory(res.history || []);
      setTotal(res.total || 0);
    } catch (err) {
      setBanner(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleVerifySingle = async (predictionId) => {
    setVerifyingId(predictionId);
    setBanner("");
    try {
      const res = await api.verifyPrediction(predictionId);
      setBanner(res.message);
      if (selectedPred && selectedPred.prediction_id === predictionId) {
        setSelectedPred(res.prediction);
      }
      await loadHistory();
    } catch (err) {
      setBanner(err.message);
    } finally {
      setVerifyingId("");
    }
  };

  const handleVerifyAllDue = async () => {
    setBanner("");
    setVerifyingId("ALL");
    try {
      const res = await api.verifyDuePredictions();
      setBanner(res.message);
      await loadHistory();
    } catch (err) {
      setBanner(err.message);
    } finally {
      setVerifyingId("");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
            Prediction History Ledger
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Immutable audit log of all {total} recorded AI predictions. Historical entries are never overwritten.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={loadHistory}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            onClick={handleVerifyAllDue}
            disabled={verifyingId === "ALL"}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            {verifyingId === "ALL" ? "Checking Market Provider..." : "Auto-Verify Due Predictions"}
          </button>
        </div>
      </div>

      {banner && (
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
          {banner}
        </div>
      )}

      {/* Search & Filter Controls */}
      <div className="fintech-card p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value.toUpperCase() })}
              placeholder="Search symbol (AAPL, NVDA)"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <input
            type="date"
            value={filters.date}
            onChange={(e) => setFilters({ ...filters, date: e.target.value })}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
            aria-label="Filter by prediction date"
          />

          <select
            value={filters.direction}
            onChange={(e) => setFilters({ ...filters, direction: e.target.value })}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="">All Directions (UP / DOWN / SIDEWAYS)</option>
            <option value="UP">UP</option>
            <option value="DOWN">DOWN</option>
            <option value="SIDEWAYS">SIDEWAYS</option>
          </select>

          <select
            value={filters.result}
            onChange={(e) => setFilters({ ...filters, result: e.target.value })}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="">All Results</option>
            <option value="CORRECT">CORRECT</option>
            <option value="INCORRECT">INCORRECT</option>
            <option value="PENDING">PENDING VERIFICATION</option>
          </select>

          <select
            value={filters.data_source}
            onChange={(e) => setFilters({ ...filters, data_source: e.target.value })}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="">All Data Sources</option>
            <option value="REAL_MARKET">Real Market Data</option>
            <option value="SIMULATED_TEST">Simulated Testing Data</option>
          </select>
        </div>
      </div>

      {/* Required 11-Column Prediction History Table */}
      <div className="fintech-card overflow-hidden p-5">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading prediction history...</div>
        ) : history.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No predictions matched your current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <th className="py-2.5 pr-3 font-semibold">Prediction ID</th>
                  <th className="py-2.5 pr-3 font-semibold">Stock Symbol</th>
                  <th className="py-2.5 pr-3 font-semibold">Starting Price</th>
                  <th className="py-2.5 pr-3 font-semibold">Predicted Price</th>
                  <th className="py-2.5 pr-3 font-semibold">Predicted Dir</th>
                  <th className="py-2.5 pr-3 font-semibold">Actual Price</th>
                  <th className="py-2.5 pr-3 font-semibold">Actual Dir</th>
                  <th className="py-2.5 pr-3 font-semibold">Prediction Date</th>
                  <th className="py-2.5 pr-3 font-semibold">Target Date</th>
                  <th className="py-2.5 pr-3 font-semibold">Result</th>
                  <th className="py-2.5 pr-3 font-semibold">Confidence</th>
                  <th className="py-2.5 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 tabular-nums dark:divide-slate-800/70">
                {history.map((p) => (
                  <tr
                    key={p.prediction_id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                  >
                    <td className="py-3 pr-3 font-mono font-semibold text-indigo-500 whitespace-nowrap">
                      {p.prediction_id}
                      <div className="mt-0.5">
                        <DataSourceBadge dataSource={p.data_source} isSimulated={p.is_simulated} />
                      </div>
                    </td>
                    <td className="py-3 pr-3 font-bold text-slate-900 dark:text-white">
                      {p.stock_symbol}
                    </td>
                    <td className="py-3 pr-3 font-mono">${p.starting_price.toFixed(2)}</td>
                    <td className="py-3 pr-3 font-mono font-semibold">${p.predicted_price.toFixed(2)}</td>
                    <td className="py-3 pr-3">
                      <DirectionBadge direction={p.predicted_direction} />
                    </td>
                    <td className="py-3 pr-3 font-mono">
                      {p.actual_price !== null ? `$${p.actual_price.toFixed(2)}` : "—"}
                    </td>
                    <td className="py-3 pr-3">
                      {p.actual_direction ? (
                        <DirectionBadge direction={p.actual_direction} />
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 pr-3 whitespace-nowrap text-slate-600 dark:text-slate-300">
                      {p.prediction_timestamp?.replace("T", " ").slice(0, 16)}
                    </td>
                    <td className="py-3 pr-3 whitespace-nowrap text-slate-600 dark:text-slate-300">
                      {p.target_timestamp?.replace("T", " ").slice(0, 16)}
                    </td>
                    <td className="py-3 pr-3">
                      <ResultBadge status={p.verification_status} result={p.prediction_result} />
                    </td>
                    <td className="py-3 pr-3 font-mono font-semibold">{p.confidence_score}%</td>
                    <td className="py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedPred(p)}
                          className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200"
                        >
                          <Eye className="h-3 w-3" />
                          Details
                        </button>
                        {p.verification_status !== "VERIFIED" && (
                          <button
                            onClick={() => handleVerifySingle(p.prediction_id)}
                            disabled={verifyingId === p.prediction_id}
                            className="inline-flex items-center gap-1 rounded-lg bg-indigo-500/15 px-2.5 py-1 text-[11px] font-semibold text-indigo-600 hover:bg-indigo-500/25 dark:text-indigo-400"
                          >
                            <CheckCircle className="h-3 w-3" />
                            Verify
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <PredictionDetailModal
        prediction={selectedPred}
        onClose={() => setSelectedPred(null)}
        onVerify={handleVerifySingle}
        verifying={verifyingId === selectedPred?.prediction_id}
      />
    </div>
  );
}

