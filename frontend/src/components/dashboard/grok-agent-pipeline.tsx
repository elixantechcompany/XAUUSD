"use client";

import { Search, Shield, Zap, Activity, TrendingUp } from "lucide-react";
import { formatPnl } from "@/lib/utils";

interface GrokAgentPipelineProps {
  activeSignalsCount?: number;
  mt5Connected?: boolean;
  openPositionsCount?: number;
  dailyPnl?: number | null;
}

export function GrokAgentPipeline({
  activeSignalsCount = 0,
  mt5Connected = false,
  openPositionsCount = 0,
  dailyPnl = 0,
}: GrokAgentPipelineProps) {
  const agents = [
    {
      id: "scout",
      name: "Scout",
      role: "Fair Value Gap & structural liquidity scanner",
      icon: Search,
      iconBg: "bg-blue-600/15 border-blue-500/30",
      iconColor: "text-blue-400",
      statusText: activeSignalsCount > 0
        ? `${activeSignalsCount} quantitative setup${activeSignalsCount > 1 ? "s" : ""} active`
        : "Scanning H1 candles for XAUUSD & BTCUSD",
      statusBadge: activeSignalsCount > 0 ? `${activeSignalsCount} ACTIVE` : "SCANNING",
      badgeBg: activeSignalsCount > 0 ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300" : "bg-blue-500/10 border-blue-500/25 text-blue-300",
      inFlight: activeSignalsCount > 0,
    },
    {
      id: "analyst",
      name: "Analyst",
      role: "Session timing & macroeconomic liquidity verification",
      icon: Shield,
      iconBg: "bg-purple-600/15 border-purple-500/30",
      iconColor: "text-purple-400",
      statusText: "Session filters & news lockout protocol active",
      statusBadge: "ARMED",
      badgeBg: "bg-purple-500/10 border-purple-500/25 text-purple-300",
      inFlight: true,
    },
    {
      id: "sniper",
      name: "Sniper",
      role: "Sub-second single MT5 terminal order dispatch",
      icon: Zap,
      iconBg: "bg-amber-600/15 border-amber-500/30",
      iconColor: "text-amber-400",
      statusText: mt5Connected
        ? "Single terminal connected (<200ms copier sync)"
        : "Awaiting local MT5 terminal heartbeat",
      statusBadge: mt5Connected ? "ONLINE" : "STANDBY",
      badgeBg: mt5Connected ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300" : "bg-amber-500/10 border-amber-500/25 text-amber-300",
      inFlight: mt5Connected,
    },
    {
      id: "risk",
      name: "Risk Guard",
      role: "Dynamic trailing stop & aggressive retracement lock",
      icon: Activity,
      iconBg: "bg-pink-600/15 border-pink-500/30",
      iconColor: "text-pink-400",
      statusText: openPositionsCount > 0
        ? `${openPositionsCount} position${openPositionsCount > 1 ? "s" : ""} protected with trailing stops`
        : "Dynamic 1.0R Breakeven and Retracement lock active",
      statusBadge: openPositionsCount > 0 ? `${openPositionsCount} PROTECTED` : "ARMED",
      badgeBg: "bg-pink-500/10 border-pink-500/25 text-pink-300",
      inFlight: openPositionsCount > 0,
    },
    {
      id: "banker",
      name: "Banker",
      role: "Systematic multi-account profit preservation",
      icon: TrendingUp,
      iconBg: "bg-emerald-600/15 border-emerald-500/30",
      iconColor: "text-emerald-400",
      statusText: dailyPnl != null && dailyPnl !== 0
        ? `Daily PnL: ${formatPnl(dailyPnl)}`
        : "Ready to bank partial profits at key SMC targets",
      statusBadge: dailyPnl != null && dailyPnl !== 0 ? formatPnl(dailyPnl) : "STANDBY",
      badgeBg: "bg-emerald-500/10 border-emerald-500/25 text-emerald-300",
      inFlight: false,
    },
  ];

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-5 shadow-[0_0_40px_rgba(0,0,0,0.4)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1B2535] pb-3">
        <h3 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
          Autonomous Pipeline
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#121821] text-text-secondary border border-[#243043]">
          5-Agent Relay
        </span>
      </div>

      {/* Agents List with Real System States */}
      <div className="space-y-2.5">
        {agents.map((agent) => {
          const Icon = agent.icon;
          return (
            <div
              key={agent.id}
              className="flex items-center justify-between p-3 rounded-inner bg-[#121821]/80 hover:bg-[#121821] border border-[#1E293B] transition-all hover:border-[#2E3D52] group"
            >
              {/* Left: Icon & Title */}
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={`w-9 h-9 rounded-xl ${agent.iconBg} border flex items-center justify-center shrink-0 shadow-sm`}
                >
                  <Icon className={`w-4 h-4 ${agent.iconColor}`} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-white group-hover:text-gold transition-colors">
                      {agent.name}
                    </span>
                    {agent.inFlight && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    )}
                  </div>
                  <p className="text-[11px] text-text-secondary truncate">
                    {agent.role}
                  </p>
                </div>
              </div>

              {/* Right: Real Status Tag & Real Count Badge */}
              <div className="flex items-center gap-2.5 shrink-0 pl-2">
                <span className="hidden sm:inline-block text-xs text-text-secondary font-mono">
                  {agent.statusText}
                </span>
                <span
                  className={`text-xs font-bold font-mono px-2.5 py-1 rounded-md border ${agent.badgeBg}`}
                >
                  {agent.statusBadge}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
