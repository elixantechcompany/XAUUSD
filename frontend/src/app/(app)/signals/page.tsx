"use client";

/**
 * Signals & Manual Trading Command Center — STRATEGY_SPEC.md v1.0
 *
 * Provides:
 * - Real-time market open/close & global session detector for XAUUSD & BTCUSD.
 * - Live algorithmic signals with explicit Reason for Entry.
 * - Interactive FVG measuring & position forecasting tools.
 * - One-click manual trade dispatch to Master MT5 Terminal & child copier accounts.
 */

import { useState, useMemo } from "react";
import { useBotStore } from "@/lib/store";
import { SignalCard } from "@/components/signals/signal-card";
import { MarketSessionDetector } from "@/components/signals/market-session-detector";
import { InteractiveForecastChart } from "@/components/charts/interactive-forecast-chart";
import { Sparkles } from "lucide-react";
import type { Instrument, Signal } from "@/lib/supabase/types";
import { cn } from "@/lib/utils";

const INSTRUMENTS: (Instrument | "ALL")[] = ["ALL", "XAUUSD"];
const STATUSES = ["ALL", "ACTIVE", "READY", "CLOSED"] as const;

const ACTIVE_STATES = new Set([
  "FVG_DETECTED", "SWEEP_CONFIRMED", "WAITING_FOR_RETRACEMENT",
  "REFERENCE_CANDLE_SAVED", "WAITING_FOR_GAP_EXIT", "GAP_EXITED",
  "WAITING_FOR_TRIGGER", "SIGNAL_READY", "RISK_CHECK", "ORDER_PENDING", "POSITION_OPEN",
]);

export default function SignalsPage() {
  const storeSignals = useBotStore((s) => s.signals);
  const [instrument, setInstrument] = useState<Instrument | "ALL">("ALL");
  const [statusFilter, setStatus] = useState<typeof STATUSES[number]>("ALL");

  // Only display real signals from Supabase — never fabricate dummy data
  const displaySignals = storeSignals;

  const filtered = useMemo(() => {
    return displaySignals.filter((s) => {
      if (instrument !== "ALL" && s.instrument !== instrument) return false;
      if (statusFilter === "ALL") return true;
      if (statusFilter === "ACTIVE") return ACTIVE_STATES.has(s.state);
      if (statusFilter === "READY") return s.state === "SIGNAL_READY";
      if (statusFilter === "CLOSED") return s.state === "CLOSED" || s.state === "EXPIRED";
      return true;
    });
  }, [displaySignals, instrument, statusFilter]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Signals & Manual Trading Hub
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-accent/10 border border-accent/30 text-accent text-xs font-semibold flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              SMC Quantitative
            </span>
          </div>
          <p className="text-sm text-text-secondary mt-1">
            Algorithmic Part 3 setups for <strong>XAUUSD</strong> and <strong>BTCUSD</strong> with entry reasons, FVG forecasting, and 1-click execution.
          </p>
        </div>
      </div>

      {/* ── 1. Global Market Session & Open/Close Detector ── */}
      <MarketSessionDetector instrument={instrument} />

      {/* ── 2. TradingView SMC Forecasting & Measuring Tool (Image 1) ── */}
      <InteractiveForecastChart initialInstrument={instrument === "BTCUSD" ? "BTCUSD" : "XAUUSD"} />

      {/* ── 3. Filters & Symbol Switcher ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface border border-border rounded-card p-3">
        {/* Symbol Switcher */}
        <div className="flex items-center gap-1.5">
          {INSTRUMENTS.map((i) => (
            <button
              key={i}
              onClick={() => setInstrument(i)}
              className={cn(
                "px-3.5 py-2 rounded-inner text-xs font-semibold transition-all min-h-[38px]",
                instrument === i
                  ? "bg-accent text-white shadow-sm"
                  : "bg-surface-2 text-text-secondary hover:text-text-primary border border-border"
              )}
            >
              {i === "ALL" ? "All Markets" : i === "XAUUSD" ? "Gold (XAUUSD)" : "Bitcoin (BTCUSD)"}
            </button>
          ))}
        </div>

        {/* State Filter */}
        <div className="flex items-center gap-1.5">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                "px-3 py-1.5 rounded-inner text-xs font-medium transition-all min-h-[34px]",
                statusFilter === s
                  ? "bg-surface-2 text-text-primary border border-accent/40 font-semibold"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ── 3. Signals Feed ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-text-secondary px-1">
          <span>Showing <strong>{filtered.length}</strong> algorithmic setup{filtered.length !== 1 ? "s" : ""}</span>
          <span className="text-[11px]">Strict 1:2.0 Minimum R:R · Dynamic Trailing SL Active</span>
        </div>

        {filtered.length === 0 ? (
          <div className="bg-surface border border-border rounded-card p-8 text-center text-text-secondary space-y-2">
            <p className="font-semibold text-text-primary">No Active Signals Match Filter</p>
            <p className="text-xs">
              The engine evaluates H1 candles continuously when sessions are active and triggers tick breakouts within &lt;50ms.
            </p>
          </div>
        ) : (
          filtered.map((sig) => (
            <SignalCard key={sig.id} signal={sig} />
          ))
        )}
      </div>
    </div>
  );
}
