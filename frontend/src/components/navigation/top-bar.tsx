"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, Sun, Moon, LogOut } from "lucide-react";
import { StatusPill } from "@/components/ui/status-pill";
import { useBotStore } from "@/lib/store";
import { getSupabaseClient } from "@/lib/supabase/client";
import { formatPrice, timeAgo } from "@/lib/utils";

export function TopBar() {
  const router = useRouter();
  const heartbeat = useBotStore((s) => s.heartbeat);
  const [signingOut, setSigningOut] = useState(false);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const isCurrentlyDark = document.documentElement.classList.contains("dark");
    setIsDark(isCurrentlyDark);
  }, []);

  function toggleTheme() {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
      localStorage.setItem("theme", "light");
    }
  }

  async function handleFastSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      localStorage.removeItem("elixan_session_active");
      const client = getSupabaseClient();
      await client.auth.signOut();
    } catch {
      // ignore
    } finally {
      router.replace("/auth/login");
    }
  }

  return (
    <header className="bg-surface border-b border-border px-4 h-14 flex items-center justify-between shrink-0 md:px-6 transition-colors duration-200 shadow-xs">
      {/* Mobile brand header */}
      <div className="flex items-center gap-2.5 md:hidden">
        <Link href="/overview" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-gold" aria-hidden />
          </div>
          <span className="font-extrabold text-xs tracking-tight text-text-primary">
            ELIXAN <span className="text-gold">QUANT</span>
          </span>
        </Link>
      </div>

      {/* Status Indicators, Theme Toggle & Fast Sign Out */}
      <div className="flex items-center gap-3 ml-auto">
        <StatusPill
          lastHeartbeatTs={heartbeat?.ts}
          executionMode={heartbeat?.execution_mode}
        />

        {heartbeat?.equity != null && (
          <span className="hidden sm:block text-xs tabular-nums text-text-secondary">
            Equity:{" "}
            <span className="text-text-primary font-bold">
              ${formatPrice(heartbeat.equity)}
            </span>
          </span>
        )}

        <span className="text-xs text-text-secondary hidden lg:block">
          {heartbeat?.ts
            ? `Updated ${timeAgo(heartbeat.ts)}`
            : "Live Stream Ready"}
        </span>

        {/* Light / Dark Mode Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          className="flex items-center gap-1.5 p-2 rounded-inner bg-surface-2 border border-border text-text-secondary hover:text-text-primary transition-all active:scale-95"
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-accent" />
          )}
          <span className="hidden sm:inline text-xs font-semibold">
            {isDark ? "Light" : "Dark"}
          </span>
        </button>

        {/* Safe & Fast Sign Out Button */}
        <button
          type="button"
          onClick={handleFastSignOut}
          disabled={signingOut}
          aria-label="Sign out"
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-text-secondary hover:text-loss hover:bg-loss/10 border border-transparent hover:border-loss/30 rounded-inner transition-colors"
        >
          <LogOut className="w-3.5 h-3.5 text-loss" />
          <span className="hidden sm:inline">{signingOut ? "Exiting..." : "Sign Out"}</span>
        </button>
      </div>
    </header>
  );
}
