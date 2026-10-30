"use client";
import { useEffect, useState } from "react";
import { getTrades } from "@/lib/supabase/queries";
import type { Trade } from "@/lib/supabase/types";
import { formatPrice, formatPnl, utcDateTime, cn } from "@/lib/utils";
import { TableRowSkeleton } from "@/components/ui/skeleton";
import { DirectionBadge } from "@/components/ui/direction-badge";
import { Download } from "lucide-react";

export default function TradesPage() {
  const [trades, setTrades]   = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [tab, setTab]         = useState<"open" | "history">("open");

  useEffect(() => {
    setLoading(true);
    getTrades({ limit: 200 })
      .then(setTrades)
      .catch(e => setError(e.message ?? "Failed to load trades"))
      .finally(() => setLoading(false));
  }, []);

  const open    = trades.filter(t => !t.close_time);
  const history = trades.filter(t =>  t.close_time);
  const shown   = tab === "open" ? open : history;

  function exportCsv() {
    const header = "ticket,instrument,side,lots,open_time,open_price,close_time,close_price,pnl,r_multiple,source";
    const rows = shown.map(t =>
      [t.ticket, t.instrument, t.side, t.lots, t.open_time, t.open_price,
       t.close_time ?? "", t.close_price ?? "", t.pnl ?? "", t.r_multiple ?? "", t.source].join(",")
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `trades_${tab}_${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Trades</h1>
        <button
          onClick={exportCsv}
          className="flex items-center gap-1.5 text-xs px-3 py-2 bg-surface-2 border border-border rounded text-text-secondary hover:text-text-primary transition-colors min-h-[44px]"
        >
          <Download className="w-3.5 h-3.5" aria-hidden /> Export CSV
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface-2 border border-border rounded p-1 w-fit">
        {(["open", "history"] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-1.5 rounded text-sm font-medium transition-colors min-h-[44px]",
              tab === t ? "bg-accent text-white" : "text-text-secondary hover:text-text-primary"
            )}
          >
            {t === "open" ? `Open (${open.length})` : `History (${history.length})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-loss/10 border border-loss/20 rounded-card p-4 text-sm text-loss">
          {error} — <button onClick={() => window.location.reload()} className="underline">Retry</button>
        </div>
      )}

      <div className="bg-surface border border-border rounded-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-secondary text-xs">
              <th className="text-left px-4 py-3">Instrument</th>
              <th className="text-left px-4 py-3">Side</th>
              <th className="text-right px-4 py-3 tabular-nums">Lots</th>
              <th className="text-right px-4 py-3 tabular-nums">Entry</th>
              {tab === "history" && <>
                <th className="text-right px-4 py-3 tabular-nums">Close</th>
                <th className="text-right px-4 py-3 tabular-nums">P/L</th>
                <th className="text-right px-4 py-3 tabular-nums">R</th>
              </>}
              <th className="text-left px-4 py-3">Time</th>
              <th className="text-left px-4 py-3">Source</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <TableRowSkeleton key={i} cols={tab === "history" ? 8 : 5} />
                ))
              : shown.length === 0
              ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-text-secondary text-sm">
                    No {tab} trades yet.
                  </td>
                </tr>
              )
              : shown.map(t => (
                <tr key={t.ticket} className="border-b border-border/50 hover:bg-surface-2/40 transition-colors">
                  <td className="px-4 py-3 font-medium text-text-primary">{t.instrument}</td>
                  <td className="px-4 py-3"><DirectionBadge direction={t.side} size="sm" /></td>
                  <td className="px-4 py-3 text-right tabular-nums text-text-primary">{t.lots}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-text-primary">{formatPrice(t.open_price)}</td>
                  {tab === "history" && <>
                    <td className="px-4 py-3 text-right tabular-nums text-text-primary">{formatPrice(t.close_price)}</td>
                    <td className={cn("px-4 py-3 text-right tabular-nums font-medium",
                      t.pnl == null ? "text-text-secondary" :
                      t.pnl >= 0 ? "text-profit" : "text-loss"
                    )}>
                      {t.pnl != null ? formatPnl(t.pnl) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
                      {t.r_multiple != null ? `${t.r_multiple >= 0 ? "+" : ""}${t.r_multiple.toFixed(2)}R` : "—"}
                    </td>
                  </>}
                  <td className="px-4 py-3 text-text-secondary text-xs">{utcDateTime(t.open_time)}</td>
                  <td className="px-4 py-3 text-text-secondary text-xs capitalize">{t.source}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>

      <p className="text-xs text-text-secondary">
        Paper, demo, and live results are never combined. Source column shows the origin of each trade.
      </p>
    </div>
  );
}
