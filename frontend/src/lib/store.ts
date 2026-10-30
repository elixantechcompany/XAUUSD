/**
 * Zustand store for live bot state.
 * Populated by Supabase Realtime subscriptions.
 */
import { create } from "zustand";
import type { Heartbeat, AccountSnapshot, Signal, Command } from "./supabase/types";

interface BotStore {
  // Latest values
  heartbeat: Heartbeat | null;
  account: AccountSnapshot | null;
  signals: Signal[];
  recentCommands: Command[];

  // Actions
  setHeartbeat:     (h: Heartbeat) => void;
  setAccount:       (a: AccountSnapshot) => void;
  upsertSignal:     (s: Signal) => void;
  addCommand:       (c: Command) => void;
  updateCommand:    (c: Command) => void;
  setInitialSignals:(signals: Signal[]) => void;
  setInitialCommands:(cmds: Command[]) => void;
}

export type { BotStore };
export const useBotStore = create<BotStore>((set) => ({
  heartbeat: null,
  account:   null,
  signals:   [],
  recentCommands: [],

  setHeartbeat: (h) => set({ heartbeat: h }),
  setAccount:   (a) => set({ account: a }),

  upsertSignal: (s) =>
    set((state) => {
      const existing = state.signals.findIndex(x => x.id === s.id);
      if (existing >= 0) {
        const next = [...state.signals];
        next[existing] = s;
        return { signals: next };
      }
      return { signals: [s, ...state.signals].slice(0, 100) };
    }),

  addCommand: (c) =>
    set((state) => ({
      recentCommands: [c, ...state.recentCommands].slice(0, 50),
    })),

  updateCommand: (c) =>
    set((state) => ({
      recentCommands: state.recentCommands.map(x => x.id === c.id ? c : x),
    })),

  setInitialSignals:  (signals) => set({ signals }),
  setInitialCommands: (cmds)    => set({ recentCommands: cmds }),
}));
