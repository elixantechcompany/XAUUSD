"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, Globe, LogOut } from "lucide-react";
import { StatusPill } from "@/components/ui/status-pill";
import { OfflineBanner } from "@/components/ui/offline-banner";
import { useBotStore } from "@/lib/store";
import { getSupabaseClient } from "@/lib/supabase/client";

export function TopBar() {
  const router = useRouter();
  const heartbeat = useBotStore((s) => s.heartbeat);
  const [signingOut, setSigningOut] = useState(false);

  async function handleFastSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      const client = getSupabaseClient();
      await client.auth.signOut();
    } catch {
      // ignore
    } finally {
      router.replace("/auth/login");
    }
  }

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

        {/* Status Indicators & Fast Sign Out */}
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

          {/* Safe & Fast Sign Out Button */}
          <button
            type="button"
            onClick={handleFastSignOut}
            disabled={signingOut}
            aria-label="Sign out"
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-text-secondary hover:text-red-400 hover:bg-red-950/20 border border-transparent hover:border-red-900/40 rounded transition-colors"
          >
            <LogOut className="w-3.5 h-3.5 text-red-400" />
            <span className="hidden sm:inline">{signingOut ? "Exiting..." : "Sign Out"}</span>
          </button>
        </div>
      </header>
    </>
  );
}
