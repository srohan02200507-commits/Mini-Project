import { NavLink } from "react-router-dom";
import {
  Activity,
  Award,
  Bot,
  Briefcase,
  Cpu,
  GitCompare,
  History,
  LayoutDashboard,
  LineChart,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";

const PRIMARY_NAV = [
  { to: "/", label: "Main Dashboard", icon: LayoutDashboard },
  { to: "/analysis", label: "Live Stock Analysis", icon: LineChart },
  { to: "/predictions", label: "AI Predictions", icon: Cpu },
  { to: "/history", label: "Prediction History", icon: History },
  { to: "/comparison", label: "Prediction Comparison", icon: GitCompare },
  { to: "/accountability", label: "Accountability Dashboard", icon: Award },
  { to: "/trading", label: "Virtual Trading", icon: Briefcase },
];

const SECONDARY_NAV = [
  { to: "/risk", label: "Risk Analysis", icon: ShieldAlert },
  { to: "/assistant", label: "AI Chat Assistant", icon: Bot },
];

export function Sidebar({ open, onClose }) {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all ${
      isActive
        ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/25"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/80 dark:hover:text-white"
    }`;

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200/80 bg-white transition-transform duration-200 dark:border-slate-800/90 dark:bg-slate-900 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-200/80 px-5 dark:border-slate-800/90">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-500/25">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <span className="block text-base font-bold tracking-tight text-slate-900 dark:text-white">
                TradeWise AI
              </span>
              <span className="block text-[10px] font-medium uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                Accountability Engine
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Core Platform
          </p>
          {PRIMARY_NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} onClick={onClose} className={linkClass}>
              <Icon className="h-[18px] w-[18px] shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Tools & Learning
          </p>
          {SECONDARY_NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={onClose} className={linkClass}>
              <Icon className="h-[18px] w-[18px] shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200/80 p-4 dark:border-slate-800/90">
          <div className="rounded-xl bg-slate-100/90 p-3 dark:bg-slate-800/70">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
              <Activity className="h-4 w-4 text-emerald-500" />
              <span>Immutable Audit Ledger</span>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              Every prediction is timestamped, verified automatically, and never overwritten.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
