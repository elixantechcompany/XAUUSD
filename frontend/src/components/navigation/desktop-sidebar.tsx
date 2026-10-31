"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  History,
  BarChart2,
  Settings2,
  Zap,
  Server,
  LogOut,
  Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getSupabaseClient } from "@/lib/supabase/client";

const NAV_ITEMS = [
  { href: "/overview",  label: "Overview",   icon: LayoutDashboard },
  { href: "/signals",   label: "Signals & FVG", icon: Radio },
  { href: "/trades",    label: "Trades",     icon: History },
  { href: "/analytics", label: "Analytics",  icon: BarChart2 },
  { href: "/accounts",  label: "Multi-Accounts", icon: Server },
  { href: "/control",   label: "Control & Risk", icon: Settings2 },
];

export function DesktopSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    try {
      await getSupabaseClient().auth.signOut();
      router.replace("/");
    } catch {
      router.replace("/");
    }
  }

  return (
    <aside className="w-60 bg-surface border-r border-border flex flex-col shrink-0 transition-colors duration-200">
      {/* Brand Logo Header */}
      <div className="p-4 border-b border-border">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 flex items-center justify-center shadow-[0_0_15px_rgba(212,175,55,0.2)] group-hover:border-gold/70 transition-all">
            <Zap className="w-4 h-4 text-gold fill-gold/20" aria-hidden />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-sm text-text-primary tracking-tight flex items-center gap-1">
              ELIXAN <span className="text-gold">QUANT</span>
            </span>
            <span className="text-[10px] text-text-secondary font-mono tracking-wider">
              AI TRADING DESK
            </span>
          </div>
        </Link>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-3 space-y-1" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3.5 py-2.5 rounded-inner text-xs font-semibold transition-all min-h-[40px]",
                active
                  ? "bg-gradient-to-r from-gold/15 to-transparent text-gold border-l-2 border-gold font-bold shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
                  : "text-text-secondary hover:text-white hover:bg-[#121821]"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className={cn("w-4 h-4 shrink-0", active ? "text-gold" : "text-text-secondary")} aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer Status & Sign Out */}
      <div className="p-3 border-t border-[#1B2535] bg-[#070A0F]/60 space-y-2">
        <div className="bg-[#121821] border border-[#243043] rounded p-2 text-[11px]">
          <div className="flex items-center justify-between text-text-secondary font-mono">
            <span>TERMINAL</span>
            <span className="text-emerald-400 font-bold">1 MT5 PROC</span>
          </div>
          <div className="flex items-center justify-between text-text-secondary font-mono mt-0.5">
            <span>FAST SWITCH</span>
            <span className="text-gold">&lt;200ms</span>
          </div>
        </div>

        <button
          onClick={handleSignOut}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-text-secondary hover:text-red-400 hover:bg-red-950/20 rounded transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
