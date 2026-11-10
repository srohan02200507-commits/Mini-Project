import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FlaskConical,
  Minus,
  Radio,
  XCircle,
} from "lucide-react";

export function DirectionBadge({ direction }) {
  const d = (direction || "SIDEWAYS").toUpperCase();
  if (d === "UP" || d === "BUY") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
        <ArrowUpRight className="h-3.5 w-3.5" />
        {d}
      </span>
    );
  }
  if (d === "DOWN" || d === "SELL") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-600 dark:text-rose-400">
        <ArrowDownRight className="h-3.5 w-3.5" />
        {d}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
      <Minus className="h-3.5 w-3.5" />
      SIDEWAYS
    </span>
  );
}

export const SignalBadge = DirectionBadge;

export function ResultBadge({ status, result }) {
  if (status !== "VERIFIED") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-500/15 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:text-slate-300">
        <Clock className="h-3.5 w-3.5" />
        PENDING VERIFICATION
      </span>
    );
  }
  if (result === "CORRECT") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 className="h-3.5 w-3.5" />
        CORRECT
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-600 dark:text-rose-400">
      <XCircle className="h-3.5 w-3.5" />
      INCORRECT
    </span>
  );
}

export const OutcomeBadge = ResultBadge;

export function DataSourceBadge({ dataSource, isSimulated }) {
  const sim = isSimulated || dataSource === "SIMULATED_TEST";
  if (sim) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
        <FlaskConical className="h-3 w-3" />
        Simulated Test
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
      <Radio className="h-3 w-3" />
      Real Market
    </span>
  );
}

export function RiskBadge({ level }) {
  const styles = {
    Low: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    Moderate: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
    Elevated: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    High: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles[level] || styles.Moderate}`}>
      {level} Risk
    </span>
  );
}
