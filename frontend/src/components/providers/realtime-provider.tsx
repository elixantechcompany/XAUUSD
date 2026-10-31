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

    // Fast initial telemetry load
    syncTelemetry();

    // Background non-blocking historical queries
    getSignals({ limit: 30 }).then(setInitialSignals).catch(() => {});
    getRecentCommands(15).then(setInitialCommands).catch(() => {});

    // Active polling interval every 3.5s to ensure zero latency
    const intervalId = setInterval(syncTelemetry, 3500);

    // Realtime subscriptions for signals & commands
    const sigSub = subscribeToSignals(upsertSignal);
    const cmdSub = subscribeToCommandUpdates(updateCommand);

    return () => {
      clearInterval(intervalId);
      sigSub.unsubscribe();
      cmdSub.unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>;
}
