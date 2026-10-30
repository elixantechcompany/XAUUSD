"use client";

import { Target, Shield, Lock, Compass } from "lucide-react";
import { formatPrice } from "@/lib/utils";

interface FvgForecastProps {
  instrument: string;
  direction: "BULLISH" | "BEARISH";
  entryPrice: number;
  slPrice: number;
  tpPrice: number;
  fvgHigh: number;
  fvgLow: number;
  triggerLevel?: number;
  sweepExtreme?: number;
  accountBalance?: number;
}

export function FvgForecastTool({
  instrument,
  direction,
  entryPrice,
  slPrice,
  tpPrice,
  fvgHigh,
  fvgLow,
  triggerLevel,
  sweepExtreme,
  accountBalance = 10000,
}: FvgForecastProps) {
  const isBullish = direction === "BULLISH";

  // Calculations
  const pipMultiplier = instrument.includes("XAU") ? 10 : 1; // 1 USD in Gold = 10 pips, 0.10 = 1 pip
  const riskDistance = Math.abs(entryPrice - slPrice);
  const rewardDistance = Math.abs(tpPrice - entryPrice);
  const rrRatio = riskDistance > 0 ? rewardDistance / riskDistance : 2.0;

  const fvgSize = Math.abs(fvgHigh - fvgLow);
  const fvgPips = (fvgSize * pipMultiplier).toFixed(1);
  const riskPips = (riskDistance * pipMultiplier).toFixed(1);
  const rewardPips = (rewardDistance * pipMultiplier).toFixed(1);

  // Profit Guardian Milestone Levels
  const breakevenLevel = isBullish ? entryPrice + riskDistance * 1.0 : entryPrice - riskDistance * 1.0;
  const lock1Level = isBullish ? entryPrice + riskDistance * 1.5 : entryPrice - riskDistance * 1.5;
  const lock2Level = isBullish ? entryPrice + riskDistance * 2.0 : entryPrice - riskDistance * 2.0;

  // 1% Dollar Risk on Account Balance
  const dollarRisk = accountBalance * 0.01;
  const dollarTargetReward = dollarRisk * rrRatio;

  // Visual layout proportions for the forecast tool
  const totalSpan = Math.max(rewardDistance + riskDistance, 0.01);
  const tpHeightPct = Math.min(Math.max((rewardDistance / totalSpan) * 100, 30), 75);
  const slHeightPct = 100 - tpHeightPct;

  return (
    <div className="bg-surface-2 border border-border rounded-card p-4 space-y-4">
      {/* ── Forecast Tool Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-accent" />
          <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            FVG Measuring & Position Forecast Tool
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 font-mono">
            R:R 1:{rrRatio.toFixed(2)}
          </span>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-profit/15 text-profit border border-profit/30 font-mono">
            Target +${dollarTargetReward.toFixed(2)}
          </span>
        </div>
      </div>

      {/* ── Visual Measuring Forecast Box (TradingView Long/Short Position Style) ── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
        {/* Left: Graphic Forecast Bar */}
        <div className="md:col-span-5 relative bg-surface border border-border rounded-inner h-64 overflow-hidden flex flex-col p-3">
          {/* Target Zone (Green) */}
          <div
            style={{ height: `${tpHeightPct}%` }}
            className="w-full bg-profit/15 border border-profit/40 rounded-t-sm flex flex-col justify-between p-2.5 relative transition-all"
          >
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-bold text-profit flex items-center gap-1">
                <Target className="w-3.5 h-3.5" /> TAKE PROFIT
              </span>
              <span className="font-mono text-profit font-bold">
                {formatPrice(tpPrice)}
              </span>
            </div>

            {/* Trailing Guardian Milestones */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-profit/80 border-t border-profit/20 pt-1">
                <span>Lock +1.0R Level:</span>
                <span className="font-mono">{formatPrice(lock2Level)}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-profit/80">
                <span>BE (1.0R Shift):</span>
                <span className="font-mono">{formatPrice(breakevenLevel)}</span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[10px] text-profit font-semibold">
                +{rewardPips} pips (+${dollarTargetReward.toFixed(2)})
              </span>
            </div>
          </div>

          {/* Center Entry Divider */}
          <div className="relative py-1 flex items-center justify-between bg-accent/20 px-2.5 border-y border-accent">
            <span className="text-[10px] font-bold text-text-primary tracking-wide">
              ENTRY PRICE
            </span>
            <span className="font-mono text-xs font-extrabold text-accent">
              {formatPrice(entryPrice)}
            </span>
          </div>

          {/* Risk Zone (Red) */}
          <div
            style={{ height: `${slHeightPct}%` }}
            className="w-full bg-loss/15 border border-loss/40 rounded-b-sm flex flex-col justify-between p-2.5 relative transition-all"
          >
            <div className="text-right">
              <span className="text-[10px] text-loss font-semibold">
                -{riskPips} pips (-${dollarRisk.toFixed(2)})
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-bold text-loss flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" /> STOP LOSS
              </span>
              <span className="font-mono text-loss font-bold">
                {formatPrice(slPrice)}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Analytical Metrics & Retracement Protection Breakdown */}
        <div className="md:col-span-7 space-y-3">
          {/* FVG Box Specification */}
          <div className="bg-surface border border-border rounded-inner p-3 space-y-2">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">
              Fair Value Gap (H1 Imbalance Zone)
            </span>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-[10px] text-text-secondary block">FVG Low</span>
                <span className="font-mono font-semibold text-text-primary">{formatPrice(fvgLow)}</span>
              </div>
              <div>
                <span className="text-[10px] text-text-secondary block">FVG High</span>
                <span className="font-mono font-semibold text-text-primary">{formatPrice(fvgHigh)}</span>
              </div>
              <div>
                <span className="text-[10px] text-text-secondary block">Gap Size</span>
                <span className="font-mono font-bold text-accent">{fvgPips} pips</span>
              </div>
            </div>
          </div>

          {/* Trailing & Retracement Guardian Card */}
          <div className="bg-surface border border-border rounded-inner p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-profit" />
                Aggressive Retracement Guardian
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-profit/10 text-profit font-semibold">
                Active in Engine
              </span>
            </div>
            <p className="text-[11px] text-text-secondary leading-relaxed">
              When market reaches <strong>1.0R</strong>, SL automatically shifts to Breakeven (+1 pip). If price peaks at <strong>&ge; 1.5R</strong> and then retraces more than <strong>40%</strong>, the guardian tightens the SL immediately to lock in banked gains.
            </p>
          </div>

          {/* Risk Management Stats */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-surface border border-border rounded-inner p-2.5">
              <span className="text-[10px] text-text-secondary block">Fixed Dollar Risk (1.0%)</span>
              <span className="font-mono font-bold text-loss mt-0.5 block">
                ${dollarRisk.toFixed(2)} USD
              </span>
            </div>
            <div className="bg-surface border border-border rounded-inner p-2.5">
              <span className="text-[10px] text-text-secondary block">Minimum Reward/Risk</span>
              <span className="font-mono font-bold text-profit mt-0.5 block">
                1:{rrRatio.toFixed(2)} (Guaranteed &ge; 1:2.0)
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
