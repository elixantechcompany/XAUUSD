"use client";

import { useEffect, useState } from "react";
import { Clock, Globe, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface SessionInfo {
  name: string;
  openUtc: number; // Hour in UTC
  closeUtc: number; // Hour in UTC
  isActive: boolean;
}

export function MarketSessionDetector({ instrument }: { instrument: "XAUUSD" | "BTCUSD" | "ALL" }) {
  const [nowUtc, setNowUtc] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNowUtc(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const currentUtcHour = nowUtc.getUTCHours() + nowUtc.getUTCMinutes() / 60;
  const currentUtcDay = nowUtc.getUTCDay(); // 0 = Sunday, 5 = Friday, 6 = Saturday

  // Forex / Gold market hours: Open Sunday 22:00 UTC to Friday 21:00 UTC
  // Daily maintenance break: 21:00 - 22:00 UTC Monday - Thursday
  const isWeekendClosed =
    currentUtcDay === 6 || // Saturday
    (currentUtcDay === 5 && currentUtcHour >= 21) || // Friday after 21:00 UTC
    (currentUtcDay === 0 && currentUtcHour < 22); // Sunday before 22:00 UTC

  const isDailyBreak = !isWeekendClosed && currentUtcHour >= 21.0 && currentUtcHour < 22.0;
  const isXauMarketOpen = !isWeekendClosed && !isDailyBreak;
  const isBtcMarketOpen = true; // Crypto 24/7/365

  // Sessions in UTC
  const sessions: SessionInfo[] = [
    {
      name: "Sydney",
      openUtc: 21,
      closeUtc: 6,
      isActive: currentUtcHour >= 21 || currentUtcHour < 6,
    },
    {
      name: "Tokyo / Asian",
      openUtc: 0,
      closeUtc: 9,
      isActive: currentUtcHour >= 0 && currentUtcHour < 9,
    },
    {
      name: "London",
      openUtc: 7,
      closeUtc: 16,
      isActive: currentUtcHour >= 7 && currentUtcHour < 16,
    },
    {
      name: "New York",
      openUtc: 12,
      closeUtc: 21,
      isActive: currentUtcHour >= 12 && currentUtcHour < 21,
    },
  ];

  // Golden Overlap: London + NY (12:00 - 16:00 UTC)
  const isGoldenOverlap = currentUtcHour >= 12 && currentUtcHour < 16 && !isWeekendClosed;

  // Format UTC Clock
  const utcClockStr = nowUtc.toUTCString().split(" ").slice(4, 5)[0] + " UTC";

  return (
    <div className="bg-surface border border-border rounded-card p-4 space-y-3.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-inner bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
            <Globe className="w-4 h-4 text-accent" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
              Global Market Session & Timing
              {isGoldenOverlap && (
                <span className="px-2 py-0.5 rounded-full bg-gold/15 border border-gold/30 text-gold text-[10px] font-bold flex items-center gap-1 uppercase tracking-wide">
                  <Zap className="w-3 h-3" /> Golden Overlap (Peak Volatility)
                </span>
              )}
            </h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Live UTC Time: <strong className="text-text-primary font-mono">{utcClockStr}</strong>
            </p>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div className="flex items-center gap-3">
          {/* XAUUSD Status */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-inner bg-surface-2 border border-border">
            <span className={cn(
              "w-2 h-2 rounded-full animate-pulse",
              isXauMarketOpen ? "bg-profit" : "bg-warning"
            )} />
            <span className="text-xs font-semibold text-text-primary">
              XAUUSD: {isXauMarketOpen ? "MARKET OPEN" : isDailyBreak ? "DAILY BREAK" : "WEEKEND CLOSED"}
            </span>
          </div>

          {/* BTCUSD Status */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-inner bg-surface-2 border border-border">
            <span className="w-2 h-2 rounded-full bg-profit animate-pulse" />
            <span className="text-xs font-semibold text-text-primary">
              BTCUSD: 24/7 OPEN
            </span>
          </div>
        </div>
      </div>

      {/* Global Session Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-border">
        {sessions.map((s) => (
          <div
            key={s.name}
            className={cn(
              "px-3 py-2 rounded-inner border transition-all text-center",
              s.isActive
                ? "bg-accent/10 border-accent/40 text-accent font-semibold"
                : "bg-surface-2/40 border-border/60 text-text-secondary"
            )}
          >
            <div className="flex items-center justify-center gap-1.5 text-xs">
              <span className={cn(
                "w-1.5 h-1.5 rounded-full",
                s.isActive ? "bg-accent" : "bg-text-secondary/40"
              )} />
              <span>{s.name}</span>
            </div>
            <span className="text-[10px] text-text-secondary mt-0.5 block">
              {s.openUtc.toString().padStart(2, "0")}:00 – {s.closeUtc.toString().padStart(2, "0")}:00 UTC
            </span>
          </div>
        ))}
      </div>

      {/* Auto-execution trigger note */}
      <div className="text-[11px] text-text-secondary flex items-center gap-1.5 bg-surface-2/60 px-3 py-1.5 rounded-inner border border-border">
        <Clock className="w-3.5 h-3.5 text-accent shrink-0" />
        <span>
          <strong>Automated Engine:</strong> The quantitative engine continuously checks H1 candle closes and fires tick breakouts within &lt;50ms when sessions are active.
        </span>
      </div>
    </div>
  );
}
