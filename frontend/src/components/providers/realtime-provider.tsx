"use client";
import { useEffect, type ReactNode } from "react";
import {
  getLatestHeartbeat, getLatestAccountSnapshot,
  getSignals, getRecentCommands,
  subscribeToHeartbeat, subscribeToSignals, subscribeToCommandUpdates,
} from "@/lib/supabase/queries";
import { useBotStore } from "@/lib/store";

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { setHeartbeat, setAccount, upsertSignal, updateCommand,
          setInitialSignals, setInitialCommands } = useBotStore();

  useEffect(() => {
    async function syncTelemetry() {
      try {
        const res = await fetch("/api/telemetry/heartbeat", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (data.heartbeat) setHeartbeat(data.heartbeat);
          if (data.snapshot) setAccount(data.snapshot);
        }
      } catch {
        // ignore
      }
    }

    // Initial load
    syncTelemetry();
    getLatestHeartbeat().then(h => { if (h) setHeartbeat(h); }).catch(() => {});
    getLatestAccountSnapshot().then(a => { if (a) setAccount(a); }).catch(() => {});
    getSignals({ limit: 50 }).then(setInitialSignals).catch(() => {});
    getRecentCommands().then(setInitialCommands).catch(() => {});

    // Active polling interval every 3.5s to ensure zero latency
    const intervalId = setInterval(syncTelemetry, 3500);

    // Realtime subscriptions
    const hbSub  = subscribeToHeartbeat(setHeartbeat);
    const sigSub = subscribeToSignals(upsertSignal);
    const cmdSub = subscribeToCommandUpdates(updateCommand);

    return () => {
      clearInterval(intervalId);
      hbSub.unsubscribe();
      sigSub.unsubscribe();
      cmdSub.unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>;
}
