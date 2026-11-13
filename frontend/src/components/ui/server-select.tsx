"use client";

import { useState, useId } from "react";
import { EXNESS_DEMO_SERVERS, EXNESS_REAL_SERVERS, isDemoServer } from "@/lib/exness-servers";
import { Server, Search, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface ServerSelectProps {
  id?: string;
  value: string;
  onChange: (server: string) => void;
  className?: string;
  preferredMode?: "DEMO" | "LIVE" | "ALL";
}

export function ServerSelect({
  id,
  value,
  onChange,
  className,
  preferredMode = "ALL",
}: ServerSelectProps) {
  const generatedId = useId();
  const selectId = id || generatedId;
  const [filter, setFilter] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const normalizedFilter = filter.trim().toLowerCase();

  const filteredDemo = EXNESS_DEMO_SERVERS.filter((s) =>
    s.toLowerCase().includes(normalizedFilter)
  );
  const filteredReal = EXNESS_REAL_SERVERS.filter((s) =>
    s.toLowerCase().includes(normalizedFilter)
  );

  const isDemo = isDemoServer(value);

  return (
    <div className="space-y-1.5 relative">
      {/* Standard Select for accessibility and instant form integration */}
      <div className="relative">
        <select
          id={selectId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "w-full bg-surface-2 border border-border rounded-inner px-3.5 py-2.5 text-sm",
            "text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/20",
            "transition-colors appearance-none cursor-pointer pr-10 min-h-[44px]",
            className
          )}
        >
          <optgroup label="── DEMO / TRIAL SERVERS (12) ──">
            {EXNESS_DEMO_SERVERS.map((srv) => (
              <option key={srv} value={srv}>
                {srv} (Demo / Paper)
              </option>
            ))}
          </optgroup>
          <optgroup label="── REAL / LIVE TRADING SERVERS (25) ──">
            {EXNESS_REAL_SERVERS.map((srv) => (
              <option key={srv} value={srv}>
                {srv} (Live Real Trading)
              </option>
            ))}
          </optgroup>
        </select>
        <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary flex items-center gap-1">
          <span
            className={cn(
              "text-[10px] font-bold px-1.5 py-0.5 rounded uppercase",
              isDemo
                ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                : "bg-profit/15 text-profit border border-profit/30"
            )}
          >
            {isDemo ? "DEMO" : "REAL"}
          </span>
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        </div>
      </div>

      {/* Helpful Quick Filter helper for power users */}
      <div className="flex items-center justify-between text-[11px] text-text-secondary px-0.5 pt-0.5">
        <span className="flex items-center gap-1">
          <Server className="w-3 h-3 text-accent" />
          <span>37 Exness MT5 servers available (12 Demo, 25 Real)</span>
        </span>
        <button
          type="button"
          onClick={() => {
            const nextServer = isDemo ? "Exness-MT5Real" : "Exness-MT5Trial12";
            onChange(nextServer);
          }}
          className="text-accent hover:underline font-semibold"
        >
          Switch to {isDemo ? "Real Server" : "Demo Server"}
        </button>
      </div>
    </div>
  );
}
