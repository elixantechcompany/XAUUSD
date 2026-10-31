"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radio, History, Settings2, Server } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/overview", label: "Desk", icon: LayoutDashboard },
  { href: "/signals",  label: "Signals",  icon: Radio },
  { href: "/trades",   label: "Trades",   icon: History },
  { href: "/accounts", label: "Accounts", icon: Server },
  { href: "/control",  label: "Risk",     icon: Settings2 },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border pb-safe z-40 transition-colors duration-200"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around h-14">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              prefetch={true}
              className={cn(
                "flex flex-col items-center gap-1 px-3 min-h-[44px] min-w-[44px] justify-center transition-colors relative",
                active ? "text-gold font-bold" : "text-text-secondary hover:text-white"
              )}
              aria-current={active ? "page" : undefined}
            >
              {active && (
                <span className="absolute top-0 w-8 h-0.5 bg-gold rounded-full shadow-[0_0_8px_rgba(212,175,55,0.8)]" />
              )}
              <Icon className={cn("w-4 h-4", active && "text-gold")} aria-hidden />
              <span className="text-[10px] leading-none">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
