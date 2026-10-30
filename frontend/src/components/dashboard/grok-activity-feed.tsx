"use client";

import { useBotStore } from "@/lib/store";
import { timeAgo, formatPrice } from "@/lib/utils";
import { Activity, Clock } from "lucide-react";

export function GrokActivityFeed() {
  const signals = useBotStore((s) => s.signals);
  const commands = useBotStore((s) => s.recentCommands);

  // Combine real signals and commands into a real event timeline
  const realEvents = [
    ...signals.slice(0, 5).map((s) => ({
      id: s.id,
      time: timeAgo(s.created_at),
      agentName: "Scout",
      agentColor: "text-blue-400",
      dotColor: "bg-blue-400",
      action: `${s.direction} ${s.instrument} setup`,
      detail: `Entry ${formatPrice(s.entry)} · SL ${formatPrice(s.stop_loss)} (R:R 1:${s.rr_ratio?.toFixed(1) ?? "2.0"})`,
      badge: s.state,
    })),
    ...commands.slice(0, 5).map((c) => ({
      id: c.id,
      time: timeAgo(c.created_at),
      agentName: "Sniper",
      agentColor: "text-amber-400",
      dotColor: "bg-amber-400",
      action: `Command: ${c.type}`,
      detail: `${c.status.toUpperCase()} execution`,
      badge: c.status,
    })),
  ].slice(0, 6);

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card p-5 shadow-[0_0_40px_rgba(0,0,0,0.4)] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1B2535] pb-3">
        <h3 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
          Activity Log
        </h3>
        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#121821] text-text-secondary border border-[#243043] font-mono">
          {realEvents.length > 0 ? (
            <span className="text-emerald-400 font-bold">{realEvents.length} events logged</span>
          ) : (
            <span>Live Stream</span>
          )}
        </span>
      </div>

      {/* Activity Timeline List */}
      {realEvents.length === 0 ? (
        <div className="py-6 text-center text-text-secondary text-xs space-y-1 font-sans">
          <Clock className="w-5 h-5 mx-auto text-text-secondary/50" />
          <p className="font-semibold text-text-primary">No Activity Logged Yet</p>
          <p className="text-[11px] text-text-secondary">
            When the quantitative engine detects setups or executes orders, real-time activity will stream here.
          </p>
        </div>
      ) : (
        <div className="space-y-3 font-mono text-xs">
          {realEvents.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between gap-2 py-1 border-b border-[#161F2E]/60 last:border-b-0"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span className={`w-2 h-2 rounded-full ${item.dotColor} shrink-0 shadow-sm`} />
                <span className="text-text-secondary/70 text-[11px] shrink-0">
                  {item.time}
                </span>
                <span className={`font-bold ${item.agentColor} shrink-0`}>
                  {item.agentName}
                </span>
                <span className="text-text-secondary truncate">
                  {item.action}:{" "}
                  <span className="text-text-primary font-medium">{item.detail}</span>
                </span>
              </div>

              {item.badge && (
                <span className="text-[10px] font-bold text-text-secondary bg-[#121821] px-2 py-0.5 rounded border border-[#243043] shrink-0">
                  {item.badge}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
