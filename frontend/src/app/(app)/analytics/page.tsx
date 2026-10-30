"use client";
import { useEffect, useState } from "react";
import { getAnalyticsByHour, getAccountHistory } from "@/lib/supabase/queries";
import type { AnalyticsByHour, AccountSnapshot } from "@/lib/supabase/types";
import { cn } from "@/lib/utils";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { format } from "date-fns";

const DAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

export default function AnalyticsPage() {
  const [heatmap, setHeatmap]   = useState<AnalyticsByHour[]>([]);
  const [history, setHistory]   = useState<AccountSnapshot[]>([]);
  const [loading, setLoading]   = useState(true);
  const [instrument, setInst]   = useState<"XAUUSD" | "BTCUSD" | "Both">("Both");

  useEffect(() => {
    Promise.all([getAnalyticsByHour(), getAccountHistory(168)])
      .then(([h, acc]) => { setHeatmap(h); setHistory(acc); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = instrument === "Both"
    ? heatmap
    : heatmap.filter(r => r.instrument === instrument);

  // Build heatmap grid: [day][hour] → avg_r
  const grid: Record<number, Record<number, AnalyticsByHour>> = {};
  for (const row of filtered) {
    if (!grid[row.day_of_week]) grid[row.day_of_week] = {};
    grid[row.day_of_week][row.hour_utc] = row;
  }

  function cellColor(r: AnalyticsByHour | undefined): string {
    if (!r || r.trade_count < 3) return "bg-surface-2 text-border";
    const val = r.avg_r ?? 0;
    if (val > 1)   return "bg-profit/30 text-profit";
    if (val > 0)   return "bg-profit/15 text-profit/70";
    if (val > -1)  return "bg-loss/15 text-loss/70";
    return "bg-loss/30 text-loss";
  }

  const equityData = history.map(s => ({
    ts:     format(new Date(s.ts), "MM/dd HH:mm"),
    equity: s.equity ?? 0,
  }));

  // Aggregate totals
  const total   = filtered.reduce((a, r) => a + r.trade_count, 0);
  const wins    = filtered.reduce((a, r) => a + r.wins, 0);
  const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) : null;
  const netPnl  = filtered.reduce((a, r) => a + (r.net_pnl ?? 0), 0);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-text-primary">Analytics</h1>
        <div className="flex gap-1 bg-surface-2 border border-border rounded p-1">
          {(["XAUUSD","BTCUSD","Both"] as const).map(i => (
            <button key={i} onClick={() => setInst(i)}
              className={cn("px-3 py-1.5 rounded text-xs font-medium transition-colors min-h-[44px]",
                instrument === i ? "bg-accent text-white" : "text-text-secondary hover:text-text-primary"
              )}>
              {i}
            </button>
          ))}
        </div>
      </div>

      {/* ── Equity curve ── */}
      {equityData.length > 1 && (
        <section className="bg-surface border border-border rounded-card p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Equity Curve (7d)</h2>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={equityData}>
              <defs>
                <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3B82F6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="ts" tick={{ fill: "#8A97A8", fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fill: "#8A97A8", fontSize: 10 }} width={60} />
              <Tooltip
                contentStyle={{ background: "#121821", border: "1px solid #243043", borderRadius: 8 }}
                labelStyle={{ color: "#8A97A8", fontSize: 11 }}
                itemStyle={{ color: "#F2F5F9" }}
              />
              <Area type="monotone" dataKey="equity" stroke="#3B82F6" fill="url(#eq)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* ── Summary stats ── */}
      {total > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Trades", value: total },
            { label: "Win Rate", value: winRate != null ? `${winRate}%` : "—" },
            { label: "Net P/L", value: `$${netPnl.toFixed(2)}` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-surface border border-border rounded-card p-3">
              <p className="text-xs text-text-secondary">{label}</p>
              <p className="text-lg font-semibold text-text-primary tabular-nums">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Hour × Day heatmap ── */}
      <section className="bg-surface border border-border rounded-card p-4">
        <h2 className="text-sm font-semibold text-text-primary mb-1">
          Performance by Hour × Day (UTC)
        </h2>
        <p className="text-xs text-text-secondary mb-3">
          Color = avg R multiple. Grey = fewer than 3 trades (unreliable sample).
        </p>

        {loading ? (
          <p className="text-text-secondary text-sm">Loading…</p>
        ) : total === 0 ? (
          <p className="text-text-secondary text-sm">
            No trade data yet. Run the bot in paper mode to populate this heatmap.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="text-xs border-collapse">
              <thead>
                <tr>
                  <th className="w-10 pr-2 text-text-secondary text-right">Day</th>
                  {Array.from({ length: 24 }, (_, h) => (
                    <th key={h} className="w-7 text-center text-text-secondary pb-1">
                      {h.toString().padStart(2,"0")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DAYS.map((day, dow) => (
                  <tr key={dow}>
                    <td className="text-text-secondary text-right pr-2 py-0.5">{day}</td>
                    {Array.from({ length: 24 }, (_, h) => {
                      const cell = grid[dow]?.[h];
                      return (
                        <td key={h}
                          className={cn("w-7 h-7 rounded text-center tabular-nums cursor-default", cellColor(cell))}
                          title={cell ? `${cell.trade_count} trades, avg R: ${cell.avg_r?.toFixed(2) ?? "—"}` : "No data"}
                        >
                          {cell && cell.trade_count >= 3 ? cell.trade_count : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="text-xs text-text-secondary">
        Analytics use only verified closed trades. Insufficient sample sizes are labelled as unreliable.
        Past results do not predict future performance.
      </p>
    </div>
  );
}
