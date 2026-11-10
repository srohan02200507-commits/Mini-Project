import { FlaskConical } from "lucide-react";

export function SimulatedBanner({ compact = false, extraText = "" }) {
  return (
    <div
      className={`flex flex-wrap items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200 ${
        compact ? "px-3 py-1.5 text-xs" : "px-4 py-2.5 text-xs sm:text-sm"
      }`}
    >
      <FlaskConical className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
      <span className="font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
        Simulated Market Data
      </span>
      <span className="text-amber-800/90 dark:text-amber-200/90">
        {extraText ||
          "All prices, AI forecasts, and virtual trades use simulated data for educational learning only—no real money or guaranteed returns."}
      </span>
    </div>
  );
}

