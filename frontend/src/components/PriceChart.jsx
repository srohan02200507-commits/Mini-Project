import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function PriceChart({ data, showSma = true, showBands = false, height = 320 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500 dark:text-slate-400">
        No simulated chart data available.
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.28} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.16)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickFormatter={(val) => val.slice(5)}
            minTickGap={24}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickFormatter={(val) => `$${val}`}
            width={62}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(15, 23, 42, 0.94)",
              borderColor: "rgba(99, 102, 241, 0.35)",
              borderRadius: "12px",
              color: "#f8fafc",
              fontSize: "12px",
            }}
            formatter={(val, name) => [
              typeof val === "number" ? `$${val.toFixed(2)}` : val,
              name,
            ]}
          />
          {showBands && (
            <>
              <Line
                type="monotone"
                dataKey="bb_upper"
                name="Bollinger Upper"
                stroke="#94a3b8"
                strokeDasharray="4 4"
                dot={false}
                strokeWidth={1.2}
              />
              <Line
                type="monotone"
                dataKey="bb_lower"
                name="Bollinger Lower"
                stroke="#94a3b8"
                strokeDasharray="4 4"
                dot={false}
                strokeWidth={1.2}
              />
            </>
          )}
          <Area
            type="monotone"
            dataKey="close"
            name="Simulated Close"
            stroke="#6366f1"
            strokeWidth={2.2}
            fill="url(#priceFill)"
          />
          {showSma && (
            <>
              <Line
                type="monotone"
                dataKey="sma_5"
                name="SMA 5"
                stroke="#10b981"
                dot={false}
                strokeWidth={1.5}
              />
              <Line
                type="monotone"
                dataKey="sma_20"
                name="SMA 20"
                stroke="#f59e0b"
                dot={false}
                strokeWidth={1.5}
              />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

