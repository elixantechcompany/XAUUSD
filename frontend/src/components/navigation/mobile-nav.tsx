"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Radio, History, BarChart2, Settings2, Server } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/",         label: "Home",     icon: LayoutDashboard },
  { href: "/signals",  label: "Signals",  icon: Radio },
  { href: "/trades",   label: "Trades",   icon: History },
  { href: "/accounts", label: "Accounts", icon: Server },
  { href: "/control",  label: "Control",  icon: Settings2 },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-surface border-t border-border pb-safe z-40"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around h-14">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 px-3 min-h-[44px] min-w-[44px] justify-center transition-colors",
                active ? "text-accent" : "text-text-secondary hover:text-text-primary"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="w-5 h-5" aria-hidden />
              <span className="text-[10px] font-medium leading-none">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
