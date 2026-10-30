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
      <div className="hidden md:flex h-screen overflow-hidden bg-[#070A0F] text-[#F2F5F9] relative">
        {/* Subtle ambient lighting */}
        <div className="absolute top-0 right-1/4 w-[600px] h-[350px] bg-blue-600/5 blur-[140px] pointer-events-none -z-10" />
        <div className="absolute bottom-10 right-10 w-[500px] h-[350px] bg-gold/5 blur-[140px] pointer-events-none -z-10" />

        <DesktopSidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TopBar />
          <main
            id="main-content"
            className="flex-1 overflow-y-auto p-6 scroll-smooth bg-gradient-to-b from-[#070A0F] via-[#090D14] to-[#070A0F]"
          >
            {children}
          </main>
        </div>
      </div>

      {/* ── Mobile: stacked, tab bar at bottom ── */}
      <div className="md:hidden flex flex-col min-h-screen bg-[#070A0F] text-[#F2F5F9]">
        <TopBar />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto pb-[72px] px-4 pt-4 scroll-smooth bg-gradient-to-b from-[#070A0F] via-[#090D14] to-[#070A0F]"
        >
          {children}
        </main>
        <MobileNav />
      </div>
    </RealtimeProvider>
  );
}
