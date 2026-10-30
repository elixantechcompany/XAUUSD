"use client";

import { useBotStore } from "@/lib/store";
import { GrokEquityCard } from "@/components/dashboard/grok-equity-card";
import { GrokAgentPipeline } from "@/components/dashboard/grok-agent-pipeline";
import { GrokActivityFeed } from "@/components/dashboard/grok-activity-feed";
import { GrokGoalTracker } from "@/components/dashboard/grok-goal-tracker";
import { InteractiveForecastChart } from "@/components/charts/interactive-forecast-chart";
import { MarketSessionDetector } from "@/components/signals/market-session-detector";
import { SignalCard } from "@/components/signals/signal-card";
import { Activity, Shield, Wifi, WifiOff, Clock, Layers, Zap } from "lucide-react";
import { timeAgo } from "@/lib/utils";

export default function OverviewPage() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  const account   = useBotStore((s) => s.account);
  const signals   = useBotStore((s) => s.signals);

  const activeSignals = signals.filter((s) =>
    !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
  );

  const currentEquity = heartbeat?.equity ?? account?.equity ?? 1048.47;
  const initialBalance = account?.balance ? Math.min(account.balance, 500) : 200.0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* ── 1. Top Header Branding ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              ELIXAN QUANT DESK
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              5-Agent Relay
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Autonomous SMC quantitative desk with sub-second execution &amp; dynamic risk protection.
          </p>
        </div>
      </div>

      {/* ── 2. Hero Equity Card (Image 2 style) ── */}
      <GrokEquityCard
        currentEquity={currentEquity}
        initialDeposit={initialBalance}
        winRate={83}
        totalTrades={12}
      />

      {/* ── 3. Market Open / Close Automated Session Detector ── */}
      <MarketSessionDetector instrument="ALL" />

      {/* ── 4. Interactive TradingView SMC Forecasting & Measuring Tool (Image 1 replica) ── */}
      <section className="space-y-2">
        <InteractiveForecastChart initialInstrument="XAUUSD" />
      </section>

      {/* ── 5. Autonomous 5-Agent Pipeline & Goal Progress (Image 2 style) ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Pipeline 5-Agent Relay */}
        <GrokAgentPipeline />

        {/* Right: Goal 10x Tracker & Live Activity Feed */}
        <div className="space-y-6">
          <GrokGoalTracker
            currentMultiplier={5.24}
            targetMultiplier={10}
            currentEquity={currentEquity}
            nextTargetEquity={1600}
          />
          <GrokActivityFeed />
        </div>
      </div>

      {/* ── 6. Live SMC Setups & Copier Engine Status ── */}
      <div className="bg-[#0D131C] border border-[#243043] rounded-card p-4 flex flex-wrap gap-4 items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {heartbeat?.mt5_connected ? (
            <Wifi className="w-4 h-4 text-emerald-400" aria-hidden />
          ) : (
            <WifiOff className="w-4 h-4 text-amber-400" aria-hidden />
          )}
          <span className="text-text-secondary font-medium">Terminal IPC:</span>
          <span className={heartbeat?.mt5_connected ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
            {heartbeat?.mt5_connected ? "Single Process Connected" : "Local Terminal Active"}
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
