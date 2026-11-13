"use client";

import { TrendingUp, TrendingDown, DollarSign, Activity, Shield } from "lucide-react";
import { formatPrice, formatPnl } from "@/lib/utils";

interface GrokEquityCardProps {
  currentEquity?: number | null;
  balance?: number | null;
  dailyPnl?: number | null;
  drawdownPct?: number | null;
  openPositions?: number;
  isOnline?: boolean;
}

export function GrokEquityCard({
  currentEquity,
  balance,
  dailyPnl = 0,
  drawdownPct = 0,
  openPositions = 0,
  isOnline = false,
}: GrokEquityCardProps) {
  const hasRealData = isOnline && currentEquity != null && currentEquity > 0;
  const displayEquity = hasRealData ? currentEquity : balance ?? 0;
  const pnl = dailyPnl ?? 0;
  const isProfit = pnl >= 0;

  return (
    <div className="bg-surface border border-border rounded-card p-6 shadow-sm relative overflow-hidden transition-all duration-200">
      {/* Top subtle gold reflection */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-gold/60 to-transparent" />

      {/* Top bar with active instruments and status pill */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-5 border-b border-border">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
          {/* Primary Asset: Gold */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-2 border border-border text-xs">
            <span className="font-bold text-gold">XAUUSD</span>
            <span className="text-text-secondary font-mono text-[11px]">H1 Liquidity & Imbalance Engine</span>
          </div>

          {/* Execution Architecture */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-2 border border-border text-xs">
            <span className="font-bold text-emerald-400">3-ORDER SYSTEM</span>
            <span className="text-text-secondary font-mono text-[11px]">Dynamic Break-Even Armed</span>
          </div>
        </div>

        {/* Live Indicator (Image 2 style) */}
        <div className="flex items-center gap-2">
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
            isOnline
              ? "bg-profit/15 border border-profit/30 text-profit"
              : "bg-surface-2 border border-border text-text-secondary"
          }`}>
            <span className={`w-2 h-2 rounded-full ${isOnline ? "bg-profit animate-pulse" : "bg-slate-400"}`} />
            <span>{isOnline ? "Live Terminal" : "Offline Standby"}</span>
          </div>

          <span className="px-2.5 py-1 text-xs font-extrabold rounded-full bg-accent/15 border border-accent/30 text-accent font-mono">
            1.0% Risk Guard
          </span>
        </div>
      </div>

      {/* Main Real Equity Display */}
      <div className="pt-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-text-secondary tracking-wide uppercase">
            Portfolio Live Equity
          </span>
          <span className="text-xs text-text-secondary font-mono">
            {hasRealData && balance != null ? (
              <>Balance: <strong className="text-text-primary">{formatPrice(balance)} USD</strong></>
            ) : (
              <span className="text-amber-500 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                Awaiting MT5 Terminal Live Sync
              </span>
            )}
          </span>
        </div>

        {/* Big Bold Real Equity Display */}
        <div className="flex flex-wrap items-baseline gap-3">
          <h2 className="text-4xl sm:text-5xl font-black text-text-primary tracking-tight font-sans">
            {hasRealData ? `$${formatPrice(displayEquity)}` : "--"}
            <span className="text-sm font-semibold text-text-secondary ml-2 font-mono">USD</span>
          </h2>
          {!hasRealData ? (
            <span className="text-xs text-text-secondary font-medium px-2.5 py-1 rounded bg-surface-2 border border-border">
              Offline Standby — Live Equity Transmitted Only When Engine Runs
            </span>
          ) : (
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-profit/15 text-profit border border-profit/30">
              {isProfit ? `+${formatPnl(pnl)}` : formatPnl(pnl)}
            </span>
          )}
        </div>

        {/* Image 2 Replica: Rising Emerald Area Curve / Sparkline */}
        <div className="w-full h-12 pt-1 relative overflow-hidden">
          <svg viewBox="0 0 400 48" className="w-full h-full preserve-3d" preserveAspectRatio="none">
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10B981" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M0,42 Q40,38 80,39 T160,34 T240,28 T320,16 T390,8 L400,6 L400,48 L0,48 Z"
              fill="url(#equityGrad)"
            />
            <path
              d="M0,42 Q40,38 80,39 T160,34 T240,28 T320,16 T390,8 L400,6"
              fill="none"
              stroke="#10B981"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <circle cx="400" cy="6" r="4" fill="#10B981" className="animate-pulse" />
          </svg>
        </div>

        {/* Real Daily PnL & Drawdown */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-border mt-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-bold flex items-center gap-1 ${isProfit ? "text-profit" : "text-loss"}`}>
              {isProfit ? <TrendingUp className="w-4 h-4 text-profit" /> : <TrendingDown className="w-4 h-4 text-loss" />}
              Daily P/L: {hasRealData ? formatPnl(pnl) : "-- USD"}
            </span>
          </div>
          <div className="text-xs font-medium text-text-secondary font-mono flex items-center gap-3">
            <span>
              Drawdown: <strong className="text-text-primary">{hasRealData && drawdownPct != null ? `${drawdownPct.toFixed(2)}%` : "0.00%"}</strong>
            </span>
            <span>
              Open: <strong className="text-accent">{openPositions} position{openPositions !== 1 ? "s" : ""}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
