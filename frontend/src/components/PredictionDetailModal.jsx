import { AlertTriangle, CheckCircle2, Clock, Layers, ShieldAlert, X } from "lucide-react";
import { DataSourceBadge, DirectionBadge, ResultBadge } from "./SignalBadge";

export function PredictionDetailModal({ prediction, onClose, onVerify, verifying = false }) {
  if (!prediction) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4 dark:border-slate-800">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-indigo-500">
                {prediction.prediction_id}
              </span>
              <DataSourceBadge
                dataSource={prediction.data_source}
                isSimulated={prediction.is_simulated}
              />
              <ResultBadge
                status={prediction.verification_status}
                result={prediction.prediction_result}
              />
            </div>
            <h3 className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">
              {prediction.stock_symbol} — {prediction.stock_name}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {prediction.model_name} ({prediction.model_version}) · Horizon: {prediction.horizon_label} ·
              Tolerance: ±{prediction.tolerance_pct}%
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Price & Direction Comparison */}
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className="text-[11px] text-slate-500">Starting Price</p>
            <p className="mt-0.5 font-mono text-base font-bold tabular-nums">
              ${prediction.starting_price.toFixed(2)}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className="text-[11px] text-slate-500">Predicted Price & Dir</p>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="font-mono text-base font-bold tabular-nums">
                ${prediction.predicted_price.toFixed(2)}
              </span>
              <DirectionBadge direction={prediction.predicted_direction} />
            </div>
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className="text-[11px] text-slate-500">Actual Price & Dir</p>
            {prediction.actual_price !== null ? (
              <div className="mt-0.5 flex items-center gap-1.5">
                <span className="font-mono text-base font-bold tabular-nums">
                  ${prediction.actual_price.toFixed(2)}
                </span>
                <DirectionBadge direction={prediction.actual_direction} />
              </div>
            ) : (
              <p className="mt-1 text-xs font-medium text-slate-400">Pending target data</p>
            )}
          </div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
            <p className="text-[11px] text-slate-500">Abs Error / Confidence</p>
            <p className="mt-0.5 font-mono text-base font-bold tabular-nums">
              {prediction.absolute_price_error !== null
                ? `$${prediction.absolute_price_error.toFixed(2)} (${prediction.price_error_pct}%)`
                : "—"}{" "}
              <span className="text-xs font-semibold text-indigo-500">
                · {prediction.confidence_score}%
              </span>
            </p>
          </div>
        </div>

        {/* Exact Timestamps */}
        <div className="mt-3 grid gap-2 rounded-xl border border-slate-200/80 p-3 text-xs dark:border-slate-800 sm:grid-cols-3">
          <div>
            <span className="text-slate-500">Predicted At:</span>
            <p className="font-mono font-medium">
              {prediction.prediction_timestamp?.replace("T", " ").slice(0, 19)} UTC
            </p>
          </div>
          <div>
            <span className="text-slate-500">Target Time:</span>
            <p className="font-mono font-medium">
              {prediction.target_timestamp?.replace("T", " ").slice(0, 19)} UTC
            </p>
          </div>
          <div>
            <span className="text-slate-500">Verified At:</span>
            <p className="font-mono font-medium">
              {prediction.verification_timestamp
                ? `${prediction.verification_timestamp.replace("T", " ").slice(0, 19)} UTC`
                : "Not verified yet"}
            </p>
          </div>
        </div>

        {/* 4-Part AI Explanation (Section 6) */}
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-indigo-500/25 bg-indigo-500/5 p-4">
            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-500">
              <CheckCircle2 className="h-4 w-4" />
              1. Why AI Predicted {prediction.predicted_direction}
            </h4>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-700 dark:text-slate-200">
              {prediction.prediction_reason}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200/80 p-4 dark:border-slate-800">
            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
              <Layers className="h-4 w-4 text-sky-500" />
              2. Historical Price Patterns Observed
            </h4>
            <div className="mt-2.5 grid gap-2.5 sm:grid-cols-2">
              {(prediction.historical_patterns || []).map((pat, i) => (
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

          <div className="rounded-xl border border-slate-200/80 p-4 dark:border-slate-800">
            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
              <Clock className="h-4 w-4 text-emerald-500" />
              3. What the Confidence Score ({prediction.confidence_score}%) Means
            </h4>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
              {prediction.confidence_meaning}
            </p>
          </div>

          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4" />
              4. Factors That Could Make This Prediction Inaccurate
            </h4>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600 dark:text-slate-300">
              {(prediction.invalidation_factors || []).map((factor, idx) => (
                <li key={idx}>{factor}</li>
              ))}
            </ul>
          </div>

          {prediction.verification_notes && (
            <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
              <span className="font-semibold">Verification Audit Log:</span>{" "}
              {prediction.verification_notes}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
          <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
            <ShieldAlert className="h-3.5 w-3.5" />
            Immutable audit record — historical predictions are never overwritten.
          </span>
          <div className="flex gap-2">
            {prediction.verification_status !== "VERIFIED" && onVerify && (
              <button
                onClick={() => onVerify(prediction.prediction_id)}
                disabled={verifying}
                className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
              >
                {verifying ? "Verifying..." : "Verify Prediction Now"}
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

