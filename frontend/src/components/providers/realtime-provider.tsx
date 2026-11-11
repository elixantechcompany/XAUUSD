"use client";

/**
 * RealtimeProvider
 *
 * Wires the Supabase Realtime subscriptions AND a polling fallback.
 * Polling runs every 8 seconds so the dashboard never stays stale even
 * when the WebSocket connection drops or Realtime is slow to deliver.
 *
 * Priority:   Realtime push  (instant, ~100ms)
 * Fallback:   HTTP poll      (every 8s, guarantees freshness)
 */
import { useEffect, useRef, type ReactNode } from "react";
import {
  getLatestHeartbeat,
  getLatestAccountSnapshot,
  getSignals,
  getRecentCommands,
  subscribeToHeartbeat,
  subscribeToSignals,
  subscribeToCommandUpdates,
} from "@/lib/supabase/queries";
import { useBotStore } from "@/lib/store";

const POLL_INTERVAL_MS = 2_000;   // 2 seconds — ultra-responsive live sync with MT5 mobile/desktop

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const {
    setHeartbeat,
    setAccount,
    upsertSignal,
    updateCommand,
    setInitialSignals,
    setInitialCommands,
  } = useBotStore();

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refreshAll() {
    try {
      const [hb, acc, sigs, cmds] = await Promise.allSettled([
        getLatestHeartbeat(),
        getLatestAccountSnapshot(),
        getSignals({ limit: 50 }),
        getRecentCommands(),
      ]);

      if (hb.status === "fulfilled" && hb.value)     setHeartbeat(hb.value);
      if (acc.status === "fulfilled" && acc.value)   setAccount(acc.value);
      if (sigs.status === "fulfilled")               setInitialSignals(sigs.value);
      if (cmds.status === "fulfilled")               setInitialCommands(cmds.value);
    } catch {
      // Non-fatal — next poll will retry
    }
  }

  useEffect(() => {
    // 1. Immediate first load
    refreshAll();

    // 2. Realtime subscriptions (instant push)
    const hbSub  = subscribeToHeartbeat(setHeartbeat);
    const sigSub = subscribeToSignals(upsertSignal);
    const cmdSub = subscribeToCommandUpdates(updateCommand);

    // 3. Polling fallback — runs regardless of Realtime status
    pollRef.current = setInterval(refreshAll, POLL_INTERVAL_MS);

    return () => {
      hbSub.unsubscribe();
      sigSub.unsubscribe();
      cmdSub.unsubscribe();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>;
}
