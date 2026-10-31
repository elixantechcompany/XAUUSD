"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase/client";
import { RealtimeProvider } from "@/components/providers/realtime-provider";
import { MobileNav }        from "@/components/navigation/mobile-nav";
import { DesktopSidebar }   from "@/components/navigation/desktop-sidebar";
import { TopBar }           from "@/components/navigation/top-bar";
import { Zap } from "lucide-react";

function checkHasSession(): boolean {
  if (typeof window === "undefined") return true;
  try {
    if (localStorage.getItem("elixan_session_active") === "1") return true;
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && (k.startsWith("sb-") || k.includes("auth-token"))) {
        const val = localStorage.getItem(k);
        if (val && val.includes("access_token")) return true;
      }
    }
    if (document.cookie.includes("sb-") && document.cookie.includes("-auth-token")) return true;
  } catch {
    // ignore
  }
  return false;
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  // Synchronous initial check ensures 0ms delay — zero full-screen blocking
  const [authorized, setAuthorized] = useState<boolean>(() => checkHasSession());

  useEffect(() => {
    const client = getSupabaseClient();
    const hasToken = checkHasSession();

    if (!hasToken) {
      setAuthorized(false);
      router.replace("/auth/login");
      return;
    }

    // Verify session in the background without blocking the UI
    client.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        try {
          localStorage.removeItem("elixan_session_active");
        } catch {
          // ignore
        }
        setAuthorized(false);
        router.replace("/auth/login");
      } else {
        try {
          localStorage.setItem("elixan_session_active", "1");
        } catch {
          // ignore
        }
      }
    }).catch(() => {
      // In case of transient network slowness, keep session active
    });

    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        try {
          localStorage.removeItem("elixan_session_active");
        } catch {
          // ignore
        }
        setAuthorized(false);
        router.replace("/auth/login");
      } else {
        try {
          localStorage.setItem("elixan_session_active", "1");
        } catch {
          // ignore
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

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
