"use client";
import { useState, useMemo } from "react";
import { useBotStore } from "@/lib/store";
import { SignalCard } from "@/components/signals/signal-card";
import type { Instrument, SignalStatus } from "@/lib/supabase/types";

const INSTRUMENTS: (Instrument | "ALL")[] = ["ALL", "XAUUSD", "BTCUSD"];
const STATUSES: (SignalStatus | "ACTIVE" | "ALL")[] = ["ALL", "ACTIVE", "new", "taken", "expired", "skipped", "cancelled", "hit_tp_or_sl"];

const STATUS_LABELS: Record<string, string> = {
  ALL:        "All",
  ACTIVE:     "Active",
  new:        "New",
  taken:      "Taken",
  expired:    "Expired",
  skipped:    "Skipped",
  cancelled:  "Cancelled",
  hit_tp_or_sl: "Closed",
};

const ACTIVE_STATES = new Set([
  "FVG_DETECTED","SWEEP_CONFIRMED","WAITING_FOR_RETRACEMENT",
  "REFERENCE_CANDLE_SAVED","WAITING_FOR_GAP_EXIT","GAP_EXITED",
  "WAITING_FOR_TRIGGER","SIGNAL_READY","RISK_CHECK","ORDER_PENDING","POSITION_OPEN",
]);

export default function SignalsPage() {
  const signals = useBotStore(s => s.signals);
  const [instrument, setInstrument] = useState<Instrument | "ALL">("ALL");
  const [statusFilter, setStatus]   = useState<string>("ALL");

  const filtered = useMemo(() => signals.filter(s => {
    if (instrument !== "ALL" && s.instrument !== instrument) return false;
    if (statusFilter === "ALL")    return true;
    if (statusFilter === "ACTIVE") return ACTIVE_STATES.has(s.state);
    return s.status === statusFilter;
  }), [signals, instrument, statusFilter]);

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold text-text-primary">Signals</h1>

      {/* ── Filters ── */}
      <div className="space-y-2">
        <div className="flex gap-2 flex-wrap">
          {INSTRUMENTS.map(i => (
            <button
              key={i}
              onClick={() => setInstrument(i)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors min-h-[44px] ${
                instrument === i
                  ? "bg-accent text-white"
                  : "bg-surface-2 text-text-secondary border border-border hover:text-text-primary"
              }`}
            >
              {i}
            </button>
          ))}
        </div>
        <div className="flex gap-2 flex-wrap">
          {STATUSES.map(s => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors min-h-[44px] ${
                statusFilter === s
                  ? "bg-accent text-white"
                  : "bg-surface-2 text-text-secondary border border-border hover:text-text-primary"
              }`}
            >
              {STATUS_LABELS[s] ?? s}
            </button>
          ))}
        </div>
      </div>

      {/* ── Results ── */}
      <div className="text-xs text-text-secondary">
        {filtered.length} signal{filtered.length !== 1 ? "s" : ""} shown
      </div>

      {filtered.length === 0 ? (
        <div className="bg-surface border border-border rounded-card p-8 text-center text-text-secondary text-sm">
          No signals match this filter. The engine evaluates H1 candles for XAUUSD and BTCUSD automatically.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(s => <SignalCard key={s.id} signal={s} />)}
        </div>
      )}

      <p className="text-xs text-text-secondary text-center pb-2">
        Trading is risky. Signals are not guaranteed.
      </p>
    </div>
  );
}
