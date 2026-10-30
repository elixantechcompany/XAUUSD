"use client";
import Link from "next/link";
import { Zap, Globe } from "lucide-react";
import { StatusPill } from "@/components/ui/status-pill";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { useBotStore } from "@/lib/store";

export function TopBar() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  return (
    <>
      <header className="bg-[#0D131C] border-b border-[#1B2535] px-4 h-14 flex items-center justify-between shrink-0 md:px-6">
        {/* Mobile brand header */}
        <div className="flex items-center gap-2.5 md:hidden">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-gold" aria-hidden />
            </div>
            <span className="font-extrabold text-xs tracking-tight text-white">
              ELIXAN <span className="text-gold">QUANT</span>
            </span>
          </Link>
        </div>

        {/* Global Landing link on desktop top right */}
        <div className="hidden md:flex items-center gap-2 text-xs text-text-secondary">
          <Link
            href="/"
            className="flex items-center gap-1.5 hover:text-gold transition-colors font-medium px-2.5 py-1 rounded bg-[#121821] border border-[#243043]"
          >
            <Globe className="w-3.5 h-3.5 text-gold" />
            Landing Page
          </Link>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-3 ml-auto">
          <StatusPill
            lastHeartbeatTs={heartbeat?.ts}
            executionMode={heartbeat?.execution_mode}
          />
          {heartbeat?.equity != null && (
            <span className="hidden sm:block text-xs tabular-nums text-text-secondary">
              Equity: <span className="text-white font-bold">
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
