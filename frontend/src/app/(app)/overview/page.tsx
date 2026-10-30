"use client";

import { useBotStore } from "@/lib/store";
import { MetricCard } from "@/components/ui/metric-card";
import { SignalCard } from "@/components/signals/signal-card";
import { CardSkeleton } from "@/components/ui/skeleton";
import { MarketSessionDetector } from "@/components/signals/market-session-detector";
import { formatPrice, formatPnl, timeAgo } from "@/lib/utils";
import {
  Activity, DollarSign, TrendingUp, TrendingDown,
  Shield, Wifi, WifiOff, Clock, Layers, Zap
} from "lucide-react";

export default function OverviewPage() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  const account   = useBotStore((s) => s.account);
  const signals   = useBotStore((s) => s.signals);

  const activeSignals = signals.filter((s) =>
    !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
  );
  const latestSignals = signals.slice(0, 3);
  const isLoading = !heartbeat && !account;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* ── Top Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            Trading Desk Overview
            <span className="px-2.5 py-0.5 rounded-full bg-accent/10 border border-accent/30 text-accent text-xs font-semibold">
              Live Terminal
            </span>
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Real-time status of your single-terminal multi-account AI quantitative desk.
          </p>
        </div>
      </div>

      {/* ── Market Session Detector ── */}
      <MarketSessionDetector instrument="ALL" />

      {/* ── Connection & Fast Copier Engine Strip ── */}
      <div className="bg-surface border border-border rounded-card p-4 flex flex-wrap gap-4 items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {heartbeat?.mt5_connected ? (
            <Wifi className="w-4 h-4 text-profit" aria-hidden />
          ) : (
            <WifiOff className="w-4 h-4 text-warning" aria-hidden />
          )}
          <span className="text-text-secondary font-medium">MT5 Bridge:</span>
          <span className={heartbeat?.mt5_connected ? "text-profit font-semibold" : "text-warning font-semibold"}>
            {heartbeat?.mt5_connected ? "Single Terminal Online (IPC Connected)" : "Waiting for MT5 Terminal"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" aria-hidden />
          <span className="text-text-secondary font-medium">Execution:</span>
          <span className="text-accent uppercase font-bold text-xs px-2 py-0.5 rounded bg-accent/10 border border-accent/20">
            {heartbeat?.execution_mode ?? "DEMO / REAL"}
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
          <span className="text-text-secondary text-xs">
            {heartbeat?.ts ? `Updated ${timeAgo(heartbeat.ts)}` : "Streaming via Supabase"}
          </span>
        </div>
      </div>

      {/* ── Financial Portfolio Metrics ── */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="Equity"
            value={formatPrice(heartbeat?.equity ?? account?.equity ?? 10000)}
            subvalue="USD"
            icon={<DollarSign className="w-4 h-4 text-accent" />}
          />
          <MetricCard
            label="Balance"
            value={formatPrice(heartbeat?.balance ?? account?.balance ?? 10000)}
            subvalue="USD"
          />
          <MetricCard
            label="Daily P/L"
            value={formatPnl(account?.daily_pnl ?? 0)}
            variant={
              account?.daily_pnl == null ? "default" :
              account.daily_pnl >= 0 ? "profit" : "loss"
            }
            icon={account?.daily_pnl != null && account.daily_pnl >= 0
              ? <TrendingUp className="w-4 h-4 text-profit" />
              : <TrendingDown className="w-4 h-4 text-loss" />}
          />
          <MetricCard
            label="Max Drawdown"
            value={account?.drawdown_pct != null ? `${account.drawdown_pct.toFixed(2)}%` : "0.00%"}
            variant="default"
          />
        </div>
      )}

      {/* ── Active SMC Setups ── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-text-primary flex items-center gap-2 uppercase tracking-wider">
            <Activity className="w-4 h-4 text-accent" aria-hidden />
            Active Quantitative Setups
            {activeSignals.length > 0 && (
              <span className="bg-accent/15 text-accent text-xs px-2 py-0.5 rounded-full font-bold">
                {activeSignals.length} Active
              </span>
            )}
          </h2>
        </div>

        {activeSignals.length === 0 ? (
          <div className="bg-surface border border-border rounded-card p-8 text-center text-text-secondary text-sm space-y-1">
            <p className="font-semibold text-text-primary">Scanning H1 Candles for XAUUSD & BTCUSD</p>
            <p className="text-xs">
              When a liquidity sweep and 3-candle FVG sequence is confirmed, setups appear here automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeSignals.slice(0, 5).map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        )}
      </section>

      {/* ── Latest Signals Feed ── */}
      {latestSignals.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Recent Signals Log</h2>
          <div className="space-y-3">
            {latestSignals.map((s) => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
