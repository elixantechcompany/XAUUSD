"use client";
import { useBotStore } from "@/lib/store";
import { MetricCard } from "@/components/ui/metric-card";
import { SignalCard } from "@/components/signals/signal-card";
import { CardSkeleton } from "@/components/ui/skeleton";
import { formatPrice, formatPnl, getBotStatus, timeAgo } from "@/lib/utils";
import {
  Activity, DollarSign, TrendingUp, TrendingDown,
  Shield, Wifi, WifiOff, Clock,
} from "lucide-react";

export default function OverviewPage() {
  const heartbeat = useBotStore(s => s.heartbeat);
  const account   = useBotStore(s => s.account);
  const signals   = useBotStore(s => s.signals);

  const status = getBotStatus(heartbeat?.ts);
  const activeSignals = signals.filter(s =>
    !["CLOSED","EXPIRED","INVALIDATED","REJECTED"].includes(s.state)
  );
  const latestSignals = signals.slice(0, 3);

  const isLoading = !heartbeat && !account;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-text-primary">Overview</h1>

      {/* ── Connection / mode strip ── */}
      <div className="bg-surface border border-border rounded-card p-4 flex flex-wrap gap-4 items-center text-sm">
        <div className="flex items-center gap-2">
          {heartbeat?.mt5_connected
            ? <Wifi className="w-4 h-4 text-profit" aria-hidden />
            : <WifiOff className="w-4 h-4 text-loss" aria-hidden />}
          <span className="text-text-secondary">MT5:</span>
          <span className={heartbeat?.mt5_connected ? "text-profit" : "text-loss"}>
            {heartbeat?.mt5_connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" aria-hidden />
          <span className="text-text-secondary">Mode:</span>
          <span className="text-accent uppercase font-medium">
            {heartbeat?.execution_mode ?? "—"}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <Clock className="w-4 h-4 text-text-secondary" aria-hidden />
          <span className="text-text-secondary text-xs">
            Last update: {heartbeat?.ts ? timeAgo(heartbeat.ts) : "Unknown"}
          </span>
        </div>
        <p className="w-full text-xs text-loss font-medium">
          Live trading is permanently disabled.
        </p>
      </div>

      {/* ── Equity metrics ── */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="Equity"
            value={formatPrice(heartbeat?.equity ?? account?.equity)}
            subvalue="USD"
            icon={<DollarSign className="w-4 h-4" />}
          />
          <MetricCard
            label="Balance"
            value={formatPrice(heartbeat?.balance ?? account?.balance)}
            subvalue="USD"
          />
          <MetricCard
            label="Daily P/L"
            value={formatPnl(account?.daily_pnl)}
            variant={
              account?.daily_pnl == null ? "default" :
              account.daily_pnl >= 0 ? "profit" : "loss"
            }
            icon={account?.daily_pnl != null && account.daily_pnl >= 0
              ? <TrendingUp className="w-4 h-4" />
              : <TrendingDown className="w-4 h-4" />}
          />
          <MetricCard
            label="Drawdown"
            value={account?.drawdown_pct != null
              ? `${account.drawdown_pct.toFixed(2)}%`
              : "—"}
            variant={
              account?.drawdown_pct == null ? "default" :
              account.drawdown_pct > 2 ? "warning" : "default"
            }
          />
        </div>
      )}

      {/* ── Active setups ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent" aria-hidden />
            Active Setups
            {activeSignals.length > 0 && (
              <span className="bg-accent/10 text-accent text-xs px-1.5 py-0.5 rounded-full">
                {activeSignals.length}
              </span>
            )}
          </h2>
        </div>
        {activeSignals.length === 0 ? (
          <div className="bg-surface border border-border rounded-card p-6 text-center text-text-secondary text-sm">
            No active setups. The engine is monitoring H1 candles for XAUUSD and BTCUSD.
          </div>
        ) : (
          <div className="space-y-3">
            {activeSignals.slice(0, 5).map(s => (
              <SignalCard key={s.id} signal={s} />
            ))}
          </div>
        )}
      </section>

      {/* ── Latest signals ── */}
      {latestSignals.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-text-primary mb-3">Recent Signals</h2>
          <div className="space-y-3">
            {latestSignals.map(s => <SignalCard key={s.id} signal={s} />)}
          </div>
        </section>
      )}

      {/* Risk note */}
      <p className="text-xs text-text-secondary text-center pb-2">
        Trading is risky. Past results do not guarantee future results. Paper mode only.
      </p>
    </div>
  );
}
