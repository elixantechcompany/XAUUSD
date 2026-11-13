"use client";

import { useState } from "react";
import { useBotStore } from "@/lib/store";
import { sendCommand } from "@/lib/supabase/queries";
import { GrokEquityCard } from "@/components/dashboard/grok-equity-card";
import { GrokAgentPipeline } from "@/components/dashboard/grok-agent-pipeline";
import { GrokActivityFeed } from "@/components/dashboard/grok-activity-feed";
import { GrokGoalTracker } from "@/components/dashboard/grok-goal-tracker";
import { InteractiveForecastChart } from "@/components/charts/interactive-forecast-chart";
import { MarketSessionDetector } from "@/components/signals/market-session-detector";
import { SignalCard } from "@/components/signals/signal-card";
import { Activity, Shield, Wifi, WifiOff, Clock, Layers, RefreshCw, CheckCircle2 } from "lucide-react";
import { timeAgo, cn } from "@/lib/utils";

export default function OverviewPage() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  const account   = useBotStore((s) => s.account);
  const signals   = useBotStore((s) => s.signals);

  const [restarting, setRestarting] = useState(false);
  const [restartMessage, setRestartMessage] = useState<string | null>(null);

  const activeSignals = signals.filter((s) =>
    !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
  );

  const isOnline =
    heartbeat != null &&
    (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 < 90 &&
    (heartbeat.mt5_connected ?? false);

  const currentEquity = heartbeat?.equity ?? account?.equity ?? null;
  const currentBalance = heartbeat?.balance ?? account?.balance ?? null;
  const dailyPnl = account?.daily_pnl ?? 0;
  const drawdownPct = account?.drawdown_pct ?? 0;
  const openPositions = account?.open_positions_count ?? account?.open_positions ?? 0;

  async function handleRestart() {
    setRestarting(true);
    setRestartMessage(null);
    try {
      await sendCommand("RESTART", { source: "overview_header" });
      setRestartMessage("Restart signal dispatched — refreshing state & accounts...");
      setTimeout(() => setRestartMessage(null), 4000);
    } catch (err: unknown) {
      setRestartMessage("Failed to dispatch restart");
      setTimeout(() => setRestartMessage(null), 4000);
    } finally {
      setRestarting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* ── 1. Top Header Branding ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-text-primary flex items-center gap-2">
              ELIXAN QUANT DESK
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Autonomous Engine
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Systematic SMC quantitative desk with sub-second execution &amp; dynamic risk protection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {restartMessage && (
            <span className="text-xs text-emerald-400 font-medium animate-fade-in flex items-center gap-1 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {restartMessage}
            </span>
          )}
          <button
            type="button"
            onClick={handleRestart}
            disabled={restarting}
            className="flex items-center gap-2 px-3.5 py-2 rounded-inner bg-surface border border-border hover:border-emerald-500/40 text-xs font-semibold text-text-primary hover:text-emerald-400 transition-all shadow-xs active:scale-95 disabled:opacity-50 min-h-[40px]"
            title="Restart trading engine, reload accounts and clear scanning cooldowns"
          >
            <RefreshCw className={cn("w-3.5 h-3.5 text-emerald-400", restarting && "animate-spin")} />
            <span>{restarting ? "Restarting..." : "Restart Engine"}</span>
          </button>
        </div>
      </div>

      {/* ── 2. Real Equity Portfolio Hero Card (Zero Dummy Data) ── */}
      <GrokEquityCard
        currentEquity={currentEquity}
        balance={currentBalance}
        dailyPnl={dailyPnl}
        drawdownPct={drawdownPct}
        openPositions={openPositions}
        isOnline={isOnline}
      />

      {/* ── 3. Market Open / Close Automated Session Detector ── */}
      <MarketSessionDetector instrument="ALL" />

      {/* ── 4. Interactive SMC Forecasting & Measuring Tool ── */}
      <section className="space-y-2">
        <InteractiveForecastChart initialInstrument="XAUUSD" />
      </section>

      {/* ── 5. Autonomous 5-Agent Pipeline & Risk Guardian ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Pipeline 5-Agent Relay with Real System States */}
        <GrokAgentPipeline
          activeSignalsCount={activeSignals.length}
          mt5Connected={isOnline}
          openPositionsCount={openPositions}
          dailyPnl={dailyPnl}
        />

        {/* Right: Risk Guardian & Real Activity Feed */}
        <div className="space-y-6">
          <GrokGoalTracker
            currentDrawdown={drawdownPct}
            maxDailyDrawdown={4.0}
            maxTrailingDrawdown={6.0}
            riskPerTradePct={1.0}
          />
          <GrokActivityFeed />
        </div>
      </div>

      {/* ── 6. Copier Engine Strip ── */}
      <div className="bg-surface border border-border rounded-card p-4 flex flex-wrap gap-4 items-center justify-between text-xs transition-colors">
        <div className="flex items-center gap-2">
          {isOnline ? (
            <Wifi className="w-4 h-4 text-emerald-400" aria-hidden />
          ) : (
            <WifiOff className="w-4 h-4 text-amber-400" aria-hidden />
          )}
          <span className="text-text-secondary font-medium">Terminal IPC:</span>
          <span className={isOnline ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
            {isOnline ? "Single Process Connected (Terminal IPC Active)" : "Terminal Standby (Run connect_exness.bat on Laptop)"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" aria-hidden />
          <span className="text-text-secondary font-medium">Risk Guardian:</span>
          <span className="text-accent uppercase font-bold text-xs px-2 py-0.5 rounded bg-accent/10 border border-accent/20">
            Dynamic Trailing SL
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-gold" aria-hidden />
          <span className="text-text-secondary font-medium">Copier Engine:</span>
          <span className="text-gold font-semibold text-xs">
            In-Process Fast Switching (&lt;200ms)
          </span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <Clock className="w-4 h-4 text-text-secondary" aria-hidden />
          <span className="text-text-secondary text-[11px]">
            {heartbeat?.ts ? `Updated ${timeAgo(heartbeat.ts)}` : "Live Realtime Sync"}
          </span>
        </div>
      </div>

      {/* ── 7. Active SMC Algorithmic Setups ── */}
      {activeSignals.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent" />
              Active Signals ({activeSignals.length})
            </h2>
          </div>
          <div className="space-y-3">
            {activeSignals.map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
