"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radio, History, BarChart2, Settings2, Zap, Server } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/",          label: "Overview",   icon: LayoutDashboard },
  { href: "/signals",   label: "Signals",    icon: Radio },
  { href: "/trades",    label: "Trades",     icon: History },
  { href: "/analytics", label: "Analytics",  icon: BarChart2 },
  { href: "/accounts",  label: "Accounts",   icon: Server },
  { href: "/control",   label: "Control",    icon: Settings2 },
];

export function DesktopSidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 bg-surface border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-5 flex items-center gap-2 border-b border-border">
        <Zap className="w-5 h-5 text-accent" aria-hidden />
        <span className="font-semibold text-text-primary text-sm">BotControl</span>
        <span className="text-xs text-text-secondary ml-auto">v1.0</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium transition-colors min-h-[44px]",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-text-secondary font-medium">PAPER MODE ONLY</p>
        <p className="text-xs text-text-secondary opacity-60 mt-0.5">Live trading disabled</p>
      </div>
    </aside>
  );
}
