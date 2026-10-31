"use client";

import { Shield, AlertCircle, Lock, Zap } from "lucide-react";

interface RiskGuardianCardProps {
  currentDrawdown?: number | null;
  maxDailyDrawdown?: number;
  maxTrailingDrawdown?: number;
  riskPerTradePct?: number;
}

export function GrokGoalTracker({
  currentDrawdown = 0,
  maxDailyDrawdown = 4.0,
  maxTrailingDrawdown = 6.0,
  riskPerTradePct = 1.0,
}: RiskGuardianCardProps) {
  const dd = currentDrawdown ?? 0;
  const dailyProgress = Math.min(100, Math.max(0, (dd / maxDailyDrawdown) * 100));

  return (
    <div className="bg-surface/90 backdrop-blur-xl border border-border rounded-card p-5 shadow-sm space-y-4 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-3">
        <h3 className="text-base font-extrabold text-text-primary tracking-tight flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" />
          Risk Guardian &amp; Limits
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-profit/15 text-profit border border-profit/30 font-mono">
          Strict 1.0% Guard
        </span>
      </div>

      {/* Daily Drawdown Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">Current Daily Drawdown</span>
          <span className="font-mono font-bold text-text-primary">
            {dd.toFixed(2)}% / {maxDailyDrawdown.toFixed(1)}% Max
          </span>
        </div>
        <div className="w-full h-2 bg-surface-2 rounded-full overflow-hidden">
          <div
            style={{ width: `${dailyProgress}%` }}
            className={`h-full rounded-full transition-all ${
              dailyProgress > 75 ? "bg-loss" : dailyProgress > 50 ? "bg-warning" : "bg-profit"
            }`}
          />
        </div>
      </div>

      {/* Risk Architecture Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs pt-1">
        <div className="bg-surface-2 border border-border rounded p-2.5">
          <span className="text-[10px] text-text-secondary block">Risk Per Trade</span>
          <span className="font-mono font-bold text-profit mt-0.5 block">
            {riskPerTradePct.toFixed(1)}% Fixed Equity
          </span>
        </div>
        <div className="bg-surface-2 border border-border rounded p-2.5">
          <span className="text-[10px] text-text-secondary block">Max Portfolio DD</span>
          <span className="font-mono font-bold text-accent mt-0.5 block">
            {maxTrailingDrawdown.toFixed(1)}% Hard Stop
          </span>
        </div>
      </div>
    </div>
  );
}
