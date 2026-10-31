"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase/client";
import { RealtimeProvider } from "@/components/providers/realtime-provider";
import { MobileNav }        from "@/components/navigation/mobile-nav";
import { DesktopSidebar }   from "@/components/navigation/desktop-sidebar";
import { TopBar }           from "@/components/navigation/top-bar";
import { Zap } from "lucide-react";

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    const client = getSupabaseClient();

    // Check existing session in cookies / localStorage
    client.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        setAuthorized(false);
        router.replace("/auth/login");
      } else {
        setAuthorized(true);
      }
    });

    // Listen for auth state changes
    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        setAuthorized(false);
        router.replace("/auth/login");
      } else {
        setAuthorized(true);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  // Loading state while verifying credentials
  if (authorized === null) {
    return (
      <div className="min-h-screen bg-[#070A0F] text-[#F2F5F9] flex flex-col items-center justify-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-gold/10 border border-gold/30 flex items-center justify-center shadow-[0_0_20px_rgba(212,175,55,0.2)]">
          <Zap className="w-6 h-6 text-gold fill-gold/20 animate-pulse" />
        </div>
        <div className="text-xs font-mono tracking-widest text-text-secondary uppercase">
          Verifying Session...
        </div>
      </div>
    );
  }

  // If unauthorized, return null while router.replace executes
  if (!authorized) {
    return null;
  }

  return (
    <RealtimeProvider>
      {/* ── Desktop: sidebar + scrollable content area ── */}
      <div className="hidden md:flex h-screen overflow-hidden bg-background text-text-primary relative transition-colors duration-200">
        {/* Subtle ambient lighting */}
        <div className="absolute top-0 right-1/4 w-[600px] h-[350px] bg-blue-600/5 dark:bg-blue-600/10 blur-[140px] pointer-events-none -z-10" />
        <div className="absolute bottom-10 right-10 w-[500px] h-[350px] bg-gold/5 dark:bg-gold/10 blur-[140px] pointer-events-none -z-10" />

        <DesktopSidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TopBar />
          <main
            id="main-content"
            className="flex-1 overflow-y-auto p-6 scroll-smooth bg-background"
          >
            {children}
          </main>
        </div>
      </div>

      {/* ── Mobile: stacked, tab bar at bottom ── */}
      <div className="md:hidden flex flex-col min-h-screen bg-background text-text-primary transition-colors duration-200">
        <TopBar />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto pb-[72px] px-4 pt-4 scroll-smooth bg-background"
        >
          {children}
        </main>
        <MobileNav />
      </div>
    </RealtimeProvider>
  );
}
