"use client";

import { useEffect, useState } from "react";
import { Clock, Globe, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface SessionInfo {
  name: string;
  openUtc: number; // Hour in UTC
  closeUtc: number; // Hour in UTC
  openEat: number; // Hour in EAT (UTC+3)
  closeEat: number; // Hour in EAT (UTC+3)
  isActive: boolean;
}

export function MarketSessionDetector({ instrument }: { instrument: "XAUUSD" | "BTCUSD" | "ALL" }) {
  const [nowUtc, setNowUtc] = useState<Date>(new Date());
  const [timeZoneMode, setTimeZoneMode] = useState<"EAT" | "UTC">("EAT");

  useEffect(() => {
    const timer = setInterval(() => setNowUtc(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const currentUtcHour = nowUtc.getUTCHours() + nowUtc.getUTCMinutes() / 60;
  const currentUtcDay = nowUtc.getUTCDay(); // 0 = Sunday, 5 = Friday, 6 = Saturday

  // East Africa Time (UTC + 3)
  const eatDate = new Date(nowUtc.getTime() + 3 * 3600 * 1000);
  const eatHourStr = eatDate.getUTCHours().toString().padStart(2, "0");
  const eatMinStr = eatDate.getUTCMinutes().toString().padStart(2, "0");
  const eatSecStr = eatDate.getUTCSeconds().toString().padStart(2, "0");
  const eatClockStr = `${eatHourStr}:${eatMinStr}:${eatSecStr} EAT (UTC+3)`;

  // Forex / Gold market hours: Open Sunday 22:00 UTC to Friday 21:00 UTC
  // Daily maintenance break: 21:00 - 22:00 UTC Monday - Thursday
  const isWeekendClosed =
    currentUtcDay === 6 || // Saturday
    (currentUtcDay === 5 && currentUtcHour >= 21) || // Friday after 21:00 UTC (00:00 Saturday EAT)
    (currentUtcDay === 0 && currentUtcHour < 22); // Sunday before 22:00 UTC (01:00 Monday EAT)

  const isDailyBreak = !isWeekendClosed && currentUtcHour >= 21.0 && currentUtcHour < 22.0;
  const isXauMarketOpen = !isWeekendClosed && !isDailyBreak;
  const isBtcMarketOpen = true; // Crypto 24/7/365

  // Sessions in East Africa Time (EAT, UTC+3) & UTC
  const sessions: SessionInfo[] = [
    {
      name: "Sydney",
      openUtc: 21,
      closeUtc: 6,
      openEat: 0,
      closeEat: 9,
      isActive: currentUtcHour >= 21 || currentUtcHour < 6,
    },
    {
      name: "Tokyo / Asian",
      openUtc: 0,
      closeUtc: 9,
      openEat: 3,
      closeEat: 12,
      isActive: currentUtcHour >= 0 && currentUtcHour < 9,
    },
    {
      name: "London",
      openUtc: 7,
      closeUtc: 16,
      openEat: 10,
      closeEat: 19,
      isActive: currentUtcHour >= 7 && currentUtcHour < 16,
    },
    {
      name: "New York",
      openUtc: 12,
      closeUtc: 21,
      openEat: 15,
      closeEat: 0,
      isActive: currentUtcHour >= 12 && currentUtcHour < 21,
    },
  ];

  // Golden Overlap: London + NY (12:00 - 16:00 UTC = 15:00 - 19:00 EAT)
  const isGoldenOverlap = currentUtcHour >= 12 && currentUtcHour < 16 && !isWeekendClosed;

  // Format UTC Clock
  const utcClockStr = nowUtc.toUTCString().split(" ").slice(4, 5)[0] + " UTC";

  return (
    <div className="bg-surface border border-border rounded-card p-4 space-y-3.5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="w-8 h-8 rounded-inner bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
            <Globe className="w-4 h-4 text-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-bold text-text-primary">
                Global Market Sessions ({timeZoneMode === "EAT" ? "East Africa Time" : "UTC"})
              </h3>
              {isGoldenOverlap && (
                <span className="px-2 py-0.5 rounded-full bg-gold/15 border border-gold/30 text-gold text-[10px] font-bold flex items-center gap-1 uppercase tracking-wide">
                  <Zap className="w-3 h-3" /> Golden Overlap (Peak Volatility)
                </span>
              )}
            </div>
            <p className="text-xs text-text-secondary mt-0.5">
              Live Session Clock:{" "}
              <strong className="text-text-primary font-mono">
                {timeZoneMode === "EAT" ? eatClockStr : utcClockStr}
              </strong>
            </p>
          </div>
        </div>

        {/* Timezone Switcher & Market Status Indicators */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Timezone toggle */}
          <div className="inline-flex rounded-inner bg-surface-2 p-0.5 border border-border text-xs font-semibold">
            <button
              onClick={() => setTimeZoneMode("EAT")}
              className={cn(
                "px-2.5 py-1 rounded transition-all",
                timeZoneMode === "EAT"
                  ? "bg-accent text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              East Africa (EAT)
            </button>
            <button
              onClick={() => setTimeZoneMode("UTC")}
              className={cn(
                "px-2.5 py-1 rounded transition-all",
                timeZoneMode === "UTC"
                  ? "bg-accent text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              UTC
            </button>
          </div>

          {/* XAUUSD Status */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-inner bg-surface-2 border border-border">
            <span
              className={cn(
                "w-2 h-2 rounded-full animate-pulse",
                isXauMarketOpen ? "bg-profit" : "bg-warning"
              )}
            />
            <span className="text-xs font-semibold text-text-primary">
              Gold (XAUUSD): {isXauMarketOpen ? "MARKET OPEN" : isDailyBreak ? "DAILY ROLLOVER BREAK" : "WEEKEND CLOSED"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-inner bg-surface-2 border border-border">
            <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
            <span className="text-xs font-semibold text-gold">
              SMC Institutional Execution
            </span>
          </div>
        </div>
      </div>

      {/* Global Session Bar with East Africa Time Hours */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-border">
        {sessions.map((s) => (
          <div
            key={s.name}
            className={cn(
              "px-3 py-2 rounded-inner border transition-all text-center",
              s.isActive
                ? "bg-accent/10 border-accent/40 text-accent font-semibold shadow-sm"
                : "bg-surface-2/40 border-border/60 text-text-secondary"
            )}
          >
            <div className="flex items-center justify-center gap-1.5 text-xs">
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  s.isActive ? "bg-accent" : "bg-text-secondary/40"
                )}
              />
              <span className="font-semibold text-text-primary">{s.name}</span>
            </div>

            {/* Display in East Africa Time prominently */}
            {timeZoneMode === "EAT" ? (
              <div className="mt-0.5">
                <span className="text-xs font-bold font-mono text-accent block">
                  {s.openEat.toString().padStart(2, "0")}:00 – {s.closeEat.toString().padStart(2, "0")}:00 EAT
                </span>
                <span className="text-[10px] text-text-secondary block">
                  ({s.openUtc.toString().padStart(2, "0")}:00 – {s.closeUtc.toString().padStart(2, "0")}:00 UTC)
                </span>
              </div>
            ) : (
              <div className="mt-0.5">
                <span className="text-xs font-bold font-mono text-text-primary block">
                  {s.openUtc.toString().padStart(2, "0")}:00 – {s.closeUtc.toString().padStart(2, "0")}:00 UTC
                </span>
                <span className="text-[10px] text-text-secondary block">
                  ({s.openEat.toString().padStart(2, "0")}:00 – {s.closeEat.toString().padStart(2, "0")}:00 EAT)
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Auto-execution trigger note */}
      <div className="text-[11px] text-text-secondary flex items-center justify-between gap-1.5 bg-surface-2/60 px-3 py-1.5 rounded-inner border border-border">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-accent shrink-0" />
          <span>
            <strong>London / NY Overlap (15:00 – 19:00 EAT):</strong> Highest institutional liquidity and cleanest H1 FVG formations.
          </span>
        </div>
        <span className="text-[10px] font-mono text-gold font-semibold shrink-0">
          EAT (UTC+3) Active
        </span>
      </div>
    </div>
  );
}
