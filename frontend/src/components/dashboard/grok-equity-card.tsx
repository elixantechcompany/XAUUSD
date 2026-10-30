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
  const hasRealData = currentEquity != null && currentEquity > 0;
  const displayEquity = hasRealData ? currentEquity : balance ?? 0;
  const pnl = dailyPnl ?? 0;
  const isProfit = pnl >= 0;

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-6 shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden">
      {/* Top subtle gold reflection */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-gold/60 to-transparent" />

      {/* Top bar with active instruments */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-5 border-b border-[#1B2535]">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
          {/* Symbol 1: Gold */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121821] border border-[#243043] text-xs">
            <span className="font-bold text-gold">XAUUSD</span>
            <span className="text-text-secondary font-mono text-[11px]">H1 Imbalance Scanning</span>
          </div>

          {/* Symbol 2: Bitcoin */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121821] border border-[#243043] text-xs">
            <span className="font-bold text-amber-400">BTCUSD</span>
            <span className="text-text-secondary font-mono text-[11px]">24/7 Market Active</span>
          </div>
        </div>

        {/* Live Indicator */}
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
          isOnline
            ? "bg-emerald-950/50 border border-emerald-800/60 text-emerald-300"
            : "bg-[#161F2E] border border-[#243043] text-text-secondary"
        }`}>
          <span className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
          <span>{isOnline ? "Live Terminal" : "Local Standby"}</span>
        </div>
      </div>

      {/* Main Real Equity Display */}
      <div className="pt-5 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-text-secondary tracking-wide">
            Portfolio Live Equity
          </span>
          {balance != null && (
            <span className="text-xs text-text-secondary font-mono">
              Balance: <strong className="text-text-primary">{formatPrice(balance)} USD</strong>
            </span>
          )}
        </div>

        {/* Big Bold Real Equity Display */}
        <div className="flex flex-wrap items-baseline gap-3">
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight font-sans">
            {hasRealData ? formatPrice(displayEquity) : "--"}
            <span className="text-sm font-semibold text-text-secondary ml-2 font-mono">USD</span>
          </h2>
        </div>

        {/* Real Daily PnL & Drawdown */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#161F2E] mt-3">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-bold flex items-center gap-1 ${isProfit ? "text-profit" : "text-loss"}`}>
              {isProfit ? <TrendingUp className="w-4 h-4 text-profit" /> : <TrendingDown className="w-4 h-4 text-loss" />}
              Daily P/L: {formatPnl(pnl)}
            </span>
          </div>
          <div className="text-xs font-medium text-text-secondary font-mono flex items-center gap-3">
            <span>
              Drawdown: <strong className="text-text-primary">{drawdownPct != null ? `${drawdownPct.toFixed(2)}%` : "0.00%"}</strong>
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
