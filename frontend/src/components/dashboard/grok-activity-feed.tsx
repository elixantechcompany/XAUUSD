"use client";

import { CheckCircle2, AlertCircle } from "lucide-react";

interface ActivityItem {
  id: string;
  time: string;
  dotColor: string;
  agentName: string;
  agentColor: string;
  action: string;
  detail: string;
  pnl?: string;
  pnlType?: "profit" | "loss";
}

export function GrokActivityFeed() {
  const activities: ActivityItem[] = [
    {
      id: "act-1",
      time: "0:26.5",
      dotColor: "bg-blue-400",
      agentName: "Scout",
      agentColor: "text-blue-400",
      action: "detected H1 Fair Value Gap on",
      detail: "XAUUSD @ 4,068.20 (R:R 1:4.7)",
    },
    {
      id: "act-2",
      time: "0:25.9",
      dotColor: "bg-pink-400",
      agentName: "Risk",
      agentColor: "text-pink-400",
      action: "trailing stop shifted to",
      detail: "Breakeven (+1.0R lock) on Gold",
    },
    {
      id: "act-3",
      time: "0:25.5",
      dotColor: "bg-amber-400",
      agentName: "Sniper",
      agentColor: "text-amber-400",
      action: "executed SHORT entry",
      detail: "0.20 lots @ 4,054.46 (0.18s fill)",
    },
    {
      id: "act-4",
      time: "0:25.0",
      dotColor: "bg-emerald-400",
      agentName: "Banker",
      agentColor: "text-emerald-400",
      action: "banked partial TP",
      detail: "XAUUSD +$320.00",
      pnl: "+$320.00",
      pnlType: "profit",
    },
    {
      id: "act-5",
      time: "0:24.2",
      dotColor: "bg-purple-400",
      agentName: "Analyst",
      agentColor: "text-purple-400",
      action: "session confirmed",
      detail: "London / NY Overlap High Liquidity",
    },
  ];

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-5 shadow-[0_0_40px_rgba(0,0,0,0.4)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1B2535] pb-3">
        <h3 className="text-base font-extrabold text-white tracking-tight">
          Activity
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#121821] text-text-secondary border border-[#243043] font-mono">
          <strong className="text-emerald-400">10 wins</strong> · <span className="text-red-400">2 losses</span>
        </span>
      </div>

      {/* Activity Timeline List (matching Image 2) */}
      <div className="space-y-3 font-mono text-xs">
        {activities.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between gap-2 py-1 border-b border-[#161F2E]/60 last:border-b-0"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {/* Dot */}
              <span className={`w-2 h-2 rounded-full ${item.dotColor} shrink-0 shadow-sm`} />
              {/* Time */}
              <span className="text-text-secondary/70 text-[11px] shrink-0">
                {item.time}
              </span>
              {/* Agent */}
              <span className={`font-bold ${item.agentColor} shrink-0`}>
                {item.agentName}
              </span>
              {/* Action text */}
              <span className="text-text-secondary truncate">
                {item.action}{" "}
                <span className="text-text-primary font-medium">{item.detail}</span>
              </span>
            </div>

            {/* Optional PnL badge */}
            {item.pnl && (
              <span className="text-[11px] font-bold text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40 shrink-0">
                {item.pnl}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
