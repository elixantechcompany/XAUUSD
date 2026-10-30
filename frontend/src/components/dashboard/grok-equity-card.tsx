"use client";

import { TrendingUp, Sparkles, Activity } from "lucide-react";

interface GrokEquityCardProps {
  currentEquity?: number;
  initialDeposit?: number;
  winRate?: number;
  totalTrades?: number;
}

export function GrokEquityCard({
  currentEquity = 1048.47,
  initialDeposit = 200.0,
  winRate = 83,
  totalTrades = 12,
}: GrokEquityCardProps) {
  const profitUsd = currentEquity - initialDeposit;
  const profitPct = ((profitUsd / initialDeposit) * 100).toFixed(0);
  const multiplier = (currentEquity / initialDeposit).toFixed(2);

  // SVG sparkline coordinates for the authentic Grok equity curve
  const points = [
    { x: 0, y: 75 },
    { x: 30, y: 73 },
    { x: 60, y: 71 },
    { x: 90, y: 68 },
    { x: 120, y: 70 },
    { x: 150, y: 64 },
    { x: 180, y: 60 },
    { x: 210, y: 55 },
    { x: 240, y: 48 },
    { x: 270, y: 38 },
    { x: 300, y: 32 },
    { x: 330, y: 25 },
    { x: 360, y: 18 },
  ];

  const polylineStr = points.map((p) => `${p.x},${p.y}`).join(" ");
  const areaStr = `${polylineStr} 360,85 0,85`;

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-6 shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden">
      {/* Top subtle glow */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent" />

      {/* Top bar with active tickers (matching Image 2) */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-5 border-b border-[#1B2535]">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
          {/* Ticker 1: Gold */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121821] border border-[#243043] text-xs">
            <span className="font-bold text-gold">XAUUSD</span>
            <span className="font-mono text-text-primary">$2,738.40</span>
            <span className="text-emerald-400 font-semibold text-[10px] bg-emerald-950/60 px-1 rounded border border-emerald-800/40">
              +1.4%
            </span>
          </div>

          {/* Ticker 2: Bitcoin */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121821] border border-[#243043] text-xs">
            <span className="font-bold text-amber-400">BTCUSD</span>
            <span className="font-mono text-text-primary">$68,920</span>
            <span className="text-emerald-400 font-semibold text-[10px] bg-emerald-950/60 px-1 rounded border border-emerald-800/40">
              +3.2%
            </span>
          </div>

          {/* Ticker 3: DXY */}
          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#121821] border border-[#243043] text-xs">
            <span className="font-bold text-slate-300">DXY</span>
            <span className="font-mono text-text-primary">104.15</span>
            <span className="text-red-400 font-semibold text-[10px] bg-red-950/60 px-1 rounded border border-red-800/40">
              -0.2%
            </span>
          </div>
        </div>

        {/* Live Indicator (Image 2 style) */}
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 text-xs font-semibold">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Live</span>
        </div>
      </div>

      {/* Main Equity Hero Metrics */}
      <div className="pt-5 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-text-secondary tracking-wide">
            Equity · started with ${initialDeposit.toFixed(0)}
          </span>
          <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-extrabold font-mono shadow-[0_0_12px_rgba(16,185,129,0.25)]">
            {multiplier}x
          </span>
        </div>

        {/* Big Bold Equity Display */}
        <div className="flex flex-wrap items-baseline gap-3">
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight font-sans">
            ${currentEquity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </h2>
        </div>

        {/* Growth & Win Rate Stats */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-emerald-400 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              +${profitUsd.toFixed(2)} (+{profitPct}%)
            </span>
          </div>
          <div className="text-xs font-medium text-text-secondary font-mono">
            <strong className="text-text-primary">{totalTrades} trades</strong> · <span className="text-emerald-400 font-bold">{winRate}% win</span>
          </div>
        </div>
      </div>

      {/* Glowing SVG Equity Curve Area (Exact curve from Image 2) */}
      <div className="relative mt-4 h-24 w-full overflow-hidden">
        <svg viewBox="0 0 360 85" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="equityGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          {/* Gradient area */}
          <polygon points={areaStr} fill="url(#equityGlow)" />
          {/* Line stroke */}
          <polyline
            fill="none"
            stroke="#10B981"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={polylineStr}
          />
          {/* End marker dot */}
          <circle cx="360" cy="18" r="4" fill="#10B981" className="animate-pulse" />
        </svg>
      </div>
    </div>
  );
}
