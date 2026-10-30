"use client";
import { Zap } from "lucide-react";
import { StatusPill } from "@/components/ui/status-pill";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { useBotStore } from "@/lib/store";

export function TopBar() {
  const heartbeat = useBotStore(s => s.heartbeat);
  return (
    <>
      <header className="bg-surface border-b border-border px-4 h-12 flex items-center justify-between shrink-0 md:px-6">
        {/* Mobile logo */}
        <div className="flex items-center gap-2 md:hidden">
          <Zap className="w-4 h-4 text-accent" aria-hidden />
          <span className="font-semibold text-sm text-text-primary">BotControl</span>
        </div>

        {/* Status */}
        <div className="flex items-center gap-3 ml-auto md:ml-0">
          <StatusPill
            lastHeartbeatTs={heartbeat?.ts}
            executionMode={heartbeat?.execution_mode}
          />
          {heartbeat?.equity != null && (
            <span className="hidden sm:block text-sm tabular-nums text-text-secondary">
              Eq: <span className="text-text-primary font-medium">
                ${heartbeat.equity.toLocaleString("en-US", { maximumFractionDigits: 2 })}
              </span>
            </span>
          )}
        </div>
      </header>
      <OfflineBanner lastHeartbeatTs={heartbeat?.ts} />
    </>
  );
}
