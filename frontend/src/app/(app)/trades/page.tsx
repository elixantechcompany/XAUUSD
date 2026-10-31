"use client";
import { useEffect, useState, useCallback } from "react";
import { getTrades } from "@/lib/supabase/queries";
import type { Trade } from "@/lib/supabase/types";
import { formatPrice, formatPnl, utcDateTime, cn } from "@/lib/utils";
import { TableRowSkeleton } from "@/components/ui/skeleton";
import { DirectionBadge } from "@/components/ui/direction-badge";
import { Download, RefreshCw, XCircle, Shield, Target } from "lucide-react";

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"open" | "history">("open");
  const [closingTicket, setClosingTicket] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchTradesList = useCallback(async () => {
    try {
      const data = await getTrades({ limit: 200 });
      setTrades(data);
      setError(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to load trades";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTradesList();
    const interval = setInterval(fetchTradesList, 3500);
    return () => clearInterval(interval);
  }, [fetchTradesList]);

  const open = trades.filter((t) => !t.close_time);
  const history = trades.filter((t) => t.close_time);
  const shown = tab === "open" ? open : history;

  async function handleClosePosition(ticket: string, symbol: string) {
    setClosingTicket(ticket);
    setNotice(null);
    try {
      const res = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket, symbol }),
      });
      const json = await res.json();
      if (res.ok && json.success) {
        setNotice(`Close order sent to Exness MT5 for ticket #${ticket}`);
        setTimeout(fetchTradesList, 1200);
      } else {
        setError(json.error || "Failed to close trade");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error closing trade";
      setError(msg);
    } finally {
      setClosingTicket(null);
    }
  }

  function exportCsv() {
    const header = "ticket,instrument,side,lots,open_time,open_price,sl,tp,close_time,close_price,pnl,r_multiple,source";
    const rows = shown.map((t) =>
      [
        t.ticket,
        t.instrument,
        t.side,
        t.lots,
        t.open_time,
        t.open_price,
        t.sl ?? "",
        t.tp ?? "",
        t.close_time ?? "",
        t.close_price ?? "",
        t.pnl ?? "",
        t.r_multiple ?? "",
        t.source,
      ].join(",")
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trades_${tab}_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Order Execution &amp; Trades Desk</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Real-time Exness MT5 execution monitor with 1:3 Risk/Reward management and instant liquidation controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setLoading(true); fetchTradesList(); }}
            className="flex items-center gap-1.5 text-xs px-3 py-2 bg-surface-2 border border-border rounded text-text-secondary hover:text-text-primary transition-colors min-h-[40px] font-semibold"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} /> Refresh
          </button>
          <button
            onClick={exportCsv}
            className="flex items-center gap-1.5 text-xs px-3 py-2 bg-surface-2 border border-border rounded text-text-secondary hover:text-text-primary transition-colors min-h-[40px] font-semibold"
          >
            <Download className="w-3.5 h-3.5" aria-hidden /> Export CSV
          </button>
        </div>
      </div>

      {notice && (
        <div className="bg-profit/10 border border-profit/30 rounded-card p-3 text-xs text-profit font-semibold flex items-center justify-between">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="underline text-[11px]">Dismiss</button>
        </div>
      )}

      {error && (
        <div className="bg-loss/10 border border-loss/20 rounded-card p-4 text-sm text-loss flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => { setError(null); fetchTradesList(); }} className="underline font-bold">Retry</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-surface-2 border border-border rounded p-1 w-fit">
        {(["open", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-1.5 rounded text-xs font-bold transition-all min-h-[38px] flex items-center gap-1.5",
              tab === t ? "bg-accent text-white shadow-xs" : "text-text-secondary hover:text-text-primary"
            )}
          >
            {t === "open" ? (
              <>
                <span className={cn("w-2 h-2 rounded-full", open.length > 0 ? "bg-emerald-400 animate-pulse" : "bg-text-secondary")} />
                <span>Live Open Positions ({open.length})</span>
              </>
            ) : (
              <span>Execution History ({history.length})</span>
            )}
          </button>
        ))}
      </div>

      <div className="bg-surface border border-border rounded-card overflow-x-auto shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-secondary text-xs uppercase tracking-wider bg-surface-2">
              <th className="text-left px-4 py-3 font-semibold">Ticket</th>
              <th className="text-left px-4 py-3 font-semibold">Instrument</th>
              <th className="text-left px-4 py-3 font-semibold">Side</th>
              <th className="text-right px-4 py-3 tabular-nums font-semibold">Lots</th>
              <th className="text-right px-4 py-3 tabular-nums font-semibold">Entry</th>
              {tab === "open" && (
                <>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">Stop Loss</th>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">1:3 RR TP</th>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">Live P/L</th>
                  <th className="text-center px-4 py-3 font-semibold">Action</th>
                </>
              )}
              {tab === "history" && (
                <>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">Close</th>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">Realized P/L</th>
                  <th className="text-right px-4 py-3 tabular-nums font-semibold">R-Multiple</th>
                </>
              )}
              <th className="text-left px-4 py-3 font-semibold">Open Time</th>
              <th className="text-left px-4 py-3 font-semibold">Source</th>
            </tr>
          </thead>
          <tbody>
            {loading && trades.length === 0 ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRowSkeleton key={i} cols={tab === "open" ? 10 : 8} />
              ))
            ) : shown.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-12 text-center text-text-secondary text-sm">
                  {tab === "open"
                    ? "No open positions active on MT5. The bot is actively scanning for 1:3 RR setups."
                    : "No closed trades recorded in history."}
                </td>
              </tr>
            ) : (
              shown.map((t) => (
                <tr
                  key={t.ticket}
                  className="border-b border-border/50 hover:bg-surface-2/40 transition-colors font-mono text-xs"
                >
                  <td className="px-4 py-3 font-bold text-text-primary">#{t.ticket}</td>
                  <td className="px-4 py-3 font-bold text-accent">{t.instrument}</td>
                  <td className="px-4 py-3">
                    <DirectionBadge direction={t.side} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-text-primary font-bold">
                    {t.lots}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-text-primary font-bold">
                    {formatPrice(t.open_price)}
                  </td>
                  {tab === "open" && (
                    <>
                      <td className="px-4 py-3 text-right tabular-nums text-loss font-semibold">
                        {t.sl ? formatPrice(t.sl) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-profit font-semibold">
                        {t.tp ? formatPrice(t.tp) : "—"}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-3 text-right tabular-nums font-extrabold text-xs",
                          t.pnl == null
                            ? "text-text-secondary"
                            : t.pnl >= 0
                            ? "text-profit"
                            : "text-loss"
                        )}
                      >
                        {t.pnl != null ? formatPnl(t.pnl) : "$0.00"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => handleClosePosition(t.ticket, t.instrument)}
                          disabled={closingTicket === t.ticket}
                          className="px-2.5 py-1 bg-loss/15 hover:bg-loss/25 text-loss border border-loss/40 rounded text-[11px] font-bold active:scale-95 transition-all inline-flex items-center gap-1"
                        >
                          {closingTicket === t.ticket ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <XCircle className="w-3 h-3" />
                          )}
                          <span>{closingTicket === t.ticket ? "Closing..." : "Close"}</span>
                        </button>
                      </td>
                    </>
                  )}
                  {tab === "history" && (
                    <>
                      <td className="px-4 py-3 text-right tabular-nums text-text-primary font-medium">
                        {t.close_price ? formatPrice(t.close_price) : "—"}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-3 text-right tabular-nums font-bold",
                          t.pnl == null
                            ? "text-text-secondary"
                            : t.pnl >= 0
                            ? "text-profit"
                            : "text-loss"
                        )}
                      >
                        {t.pnl != null ? formatPnl(t.pnl) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
                        {t.r_multiple != null
                          ? `${t.r_multiple >= 0 ? "+" : ""}${t.r_multiple.toFixed(2)}R`
                          : "—"}
                      </td>
                    </>
                  )}
                  <td className="px-4 py-3 text-text-secondary text-[11px]">
                    {utcDateTime(t.open_time)}
                  </td>
                  <td className="px-4 py-3 text-text-secondary text-[11px] uppercase font-bold">
                    {t.source}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between text-xs text-text-secondary p-2 bg-surface-2 border border-border rounded">
        <span>Strict institutional risk management: Every trade enforced with broker-side Stop Loss and 1:3 RR Take Profit.</span>
        <span className="font-mono">Account #476719466 (Exness Demo)</span>
      </div>
    </div>
  );
}
