"use client";

import { Search, Shield, Zap, Activity, TrendingUp, CheckCircle2 } from "lucide-react";

interface AgentStatus {
  id: string;
  name: string;
  role: string;
  icon: typeof Search;
  iconBg: string;
  iconColor: string;
  statusText: string;
  statusBadge: string;
  badgeBg: string;
  badgeColor: string;
  inFlight?: boolean;
}

export function GrokAgentPipeline() {
  const agents: AgentStatus[] = [
    {
      id: "scout",
      name: "Scout",
      role: "finds new FVG setups & structural liquidity",
      icon: Search,
      iconBg: "bg-blue-600/15 border-blue-500/30",
      iconColor: "text-blue-400",
      statusText: "XAUUSD Bearish H1 FVG spotted",
      statusBadge: "14.1k setups",
      badgeBg: "bg-blue-500/10 border-blue-500/25",
      badgeColor: "text-blue-300",
      inFlight: true,
    },
    {
      id: "analyst",
      name: "Analyst",
      role: "session timing & market open/close check",
      icon: Shield,
      iconBg: "bg-purple-600/15 border-purple-500/30",
      iconColor: "text-purple-400",
      statusText: "London / NY Golden Overlap ACTIVE",
      statusBadge: "96% pass",
      badgeBg: "bg-purple-500/10 border-purple-500/25",
      badgeColor: "text-purple-300",
      inFlight: true,
    },
    {
      id: "sniper",
      name: "Sniper",
      role: "executes entries with sub-second precision",
      icon: Zap,
      iconBg: "bg-amber-600/15 border-amber-500/30",
      iconColor: "text-amber-400",
      statusText: "ready · 0.18s fills",
      statusBadge: "13 fills",
      badgeBg: "bg-amber-500/10 border-amber-500/25",
      badgeColor: "text-amber-300",
      inFlight: true,
    },
    {
      id: "risk",
      name: "Risk Guard",
      role: "dynamic trailing stop & retracement protection",
      icon: Activity,
      iconBg: "bg-pink-600/15 border-pink-500/30",
      iconColor: "text-pink-400",
      statusText: "+34% trailed to BE",
      statusBadge: "1 open",
      badgeBg: "bg-pink-500/10 border-pink-500/25",
      badgeColor: "text-pink-300",
      inFlight: false,
    },
    {
      id: "banker",
      name: "Banker",
      role: "exits & banks profit systematically",
      icon: TrendingUp,
      iconBg: "bg-emerald-600/15 border-emerald-500/30",
      iconColor: "text-emerald-400",
      statusText: "locking banked profits",
      statusBadge: "+$701.00",
      badgeBg: "bg-emerald-500/10 border-emerald-500/25",
      badgeColor: "text-emerald-300",
      inFlight: false,
    },
  ];

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-5 shadow-[0_0_40px_rgba(0,0,0,0.4)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1B2535] pb-3">
        <h3 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
          Pipeline
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#121821] text-text-secondary border border-[#243043]">
          5 agents · <span className="text-emerald-400">3 in flight</span>
        </span>
      </div>

      {/* Agents List (Matching Image 2) */}
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

              {/* Right: Status Tag & Count Badge */}
              <div className="flex items-center gap-2.5 shrink-0 pl-2">
                <span className="hidden sm:inline-block text-xs text-text-secondary font-mono">
                  {agent.statusText}
                </span>
                <span
                  className={`text-xs font-bold font-mono px-2.5 py-1 rounded-md border ${agent.badgeBg} ${agent.badgeColor}`}
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
