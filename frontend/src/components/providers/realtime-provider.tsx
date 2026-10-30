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
    // Initial load
    getLatestHeartbeat().then(h => { if (h) setHeartbeat(h); }).catch(() => {});
    getLatestAccountSnapshot().then(a => { if (a) setAccount(a); }).catch(() => {});
    getSignals({ limit: 50 }).then(setInitialSignals).catch(() => {});
    getRecentCommands().then(setInitialCommands).catch(() => {});

    // Realtime subscriptions
    const hbSub  = subscribeToHeartbeat(setHeartbeat);
    const sigSub = subscribeToSignals(upsertSignal);
    const cmdSub = subscribeToCommandUpdates(updateCommand);

    return () => {
      hbSub.unsubscribe();
      sigSub.unsubscribe();
      cmdSub.unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>;
}
