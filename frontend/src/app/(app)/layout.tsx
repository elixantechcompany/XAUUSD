"use client";

/**
 * Authenticated app shell layout.
 *
 * Applied to all routes EXCEPT /auth/* because those live outside this
 * route group. The RealtimeProvider wires up Supabase live subscriptions
 * once and keeps them alive for the whole session.
 */
import { RealtimeProvider } from "@/components/providers/realtime-provider";
import { MobileNav }        from "@/components/navigation/mobile-nav";
import { DesktopSidebar }   from "@/components/navigation/desktop-sidebar";
import { TopBar }           from "@/components/navigation/top-bar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RealtimeProvider>
      {/* ── Desktop: sidebar + scrollable content area ── */}
      <div className="hidden md:flex h-screen overflow-hidden">
        <DesktopSidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TopBar />
          <main
            id="main-content"
            className="flex-1 overflow-y-auto p-6 scroll-smooth"
          >
            {children}
          </main>
        </div>
      </div>

      {/* ── Mobile: stacked, tab bar at bottom ── */}
      <div className="md:hidden flex flex-col min-h-screen">
        <TopBar />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto pb-[72px] px-4 pt-4 scroll-smooth"
        >
          {children}
        </main>
        <MobileNav />
      </div>
    </RealtimeProvider>
  );
}
