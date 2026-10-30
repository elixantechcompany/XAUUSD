"use client";

import { useState, type ReactNode } from "react";
import { sendCommand } from "@/lib/supabase/queries";
import { useBotStore } from "@/lib/store";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { cn, timeAgo } from "@/lib/utils";
import type { CommandType, Command, CommandStatus } from "@/lib/supabase/types";
import {
  Play,
  Pause,
  Zap,
  Newspaper,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";

// ── Typed icon map ─────────────────────────────────────────────────────────────
// Defined as a function to avoid ReactNode return type issues before install
function statusIcon(status: CommandStatus): ReactNode {
  switch (status) {
    case "pending": return <Clock className="w-3.5 h-3.5 text-warning" aria-hidden />;
    case "done":    return <CheckCircle2 className="w-3.5 h-3.5 text-profit" aria-hidden />;
    case "failed":
    case "expired": return <XCircle className="w-3.5 h-3.5 text-loss" aria-hidden />;
  }
}

const CMD_NOTE: Record<CommandStatus, string> = {
  pending: "QUEUED — NOT YET EXECUTED",
  done:    "Acknowledged by engine",
  failed:  "Engine reported failure",
  expired: "Command expired before execution",
};

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ControlPage() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  const commands  = useBotStore((s) => s.recentCommands);
  const [sending, setSending]    = useState(false);
  const [newsSymbol, setNewsSym] = useState<"XAUUSD" | "BTCUSD">("XAUUSD");
  const [error, setError]        = useState<string | null>(null);

  const isOnline =
    heartbeat != null &&
    (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 < 60;

  async function dispatch(
    type: CommandType,
    payload: Record<string, unknown> = {}
  ): Promise<void> {
    setSending(true);
    setError(null);
    try {
      await sendCommand(type, payload);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send command");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold text-text-primary">Bot Control</h1>

      {/* Offline banner */}
      {!isOnline && (
        <div className="bg-loss/10 border border-loss/30 rounded-card p-4 text-sm text-loss">
          Engine is offline. Commands will be queued and marked{" "}
          <strong>NOT YET EXECUTED</strong> until the engine reconnects.
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-loss/10 border border-loss/20 rounded-card p-3 text-sm text-loss">
          {error}
        </div>
      )}

      {/* Main controls */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Engine Commands</h2>

        <div className="grid grid-cols-2 gap-3">
          <ConfirmDialog
            title="Pause new entries"
            description="The engine stops generating new entry signals. Open positions and their protective stops are not affected."
            confirmLabel="Pause"
            onConfirm={() => dispatch("PAUSE")}
          >
            <button
              disabled={sending}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-surface-2 border border-border rounded font-medium text-sm text-text-primary hover:bg-border transition-colors disabled:opacity-40 min-h-[44px]"
            >
              <Pause className="w-4 h-4" aria-hidden />
              Pause
            </button>
          </ConfirmDialog>

          <ConfirmDialog
            title="Resume monitoring"
            description="The engine will resume evaluating new setups. Review current risk state first."
            confirmLabel="Resume"
            onConfirm={() => dispatch("RESUME")}
          >
            <button
              disabled={sending}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-accent/10 border border-accent/30 rounded font-medium text-sm text-accent hover:bg-accent/20 transition-colors disabled:opacity-40 min-h-[44px]"
            >
              <Play className="w-4 h-4" aria-hidden />
              Resume
            </button>
          </ConfirmDialog>
        </div>

        {/* Kill switch */}
        <ConfirmDialog
          title="KILL SWITCH — halt all new submissions"
          description="Immediately blocks all new order submissions. Does NOT remove protective stops from open positions. Only a manual resume clears this."
          confirmLabel="ACTIVATE KILL SWITCH"
          danger
          requireTyped="KILL"
          onConfirm={() => dispatch("KILL")}
        >
          <button
            disabled={sending}
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-loss/10 border border-loss/30 rounded font-medium text-sm text-loss hover:bg-loss/20 transition-colors disabled:opacity-40 min-h-[44px]"
          >
            <Zap className="w-4 h-4" aria-hidden />
            Kill Switch
          </button>
        </ConfirmDialog>

        <p className="text-xs text-text-secondary">
          Starting monitoring never enables live trading. All orders run in paper mode until explicitly upgraded.
        </p>
      </section>

      {/* News lockout */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Manual News Lockout</h2>
        <p className="text-xs text-text-secondary">
          Blocks new entries for the selected symbol. Does not remove existing protective stops.
        </p>

        <div className="flex gap-2">
          {(["XAUUSD", "BTCUSD"] as const).map((sym) => (
            <button
              key={sym}
              onClick={() => setNewsSym(sym)}
              className={cn(
                "px-3 py-2 rounded text-sm font-medium transition-colors min-h-[44px]",
                newsSymbol === sym
                  ? "bg-accent text-white"
                  : "bg-surface-2 border border-border text-text-secondary hover:text-text-primary"
              )}
            >
              {sym}
            </button>
          ))}
        </div>

        <div className="flex gap-3 flex-wrap">
          <ConfirmDialog
            title={`Lock news — ${newsSymbol}`}
            description={`Block new entries for ${newsSymbol} until manually cleared. Open position stops are not affected.`}
            confirmLabel="Lock"
            onConfirm={() => dispatch("NEWS_LOCK", { symbol: newsSymbol, locked: true })}
          >
            <button
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2.5 bg-warning/10 border border-warning/30 rounded text-sm text-warning font-medium hover:bg-warning/20 transition-colors min-h-[44px]"
            >
              <Newspaper className="w-4 h-4" aria-hidden />
              Lock {newsSymbol}
            </button>
          </ConfirmDialog>

          <ConfirmDialog
            title={`Clear news lock — ${newsSymbol}`}
            description={`Allow new entries to resume for ${newsSymbol}.`}
            confirmLabel="Clear Lock"
            onConfirm={() => dispatch("NEWS_LOCK", { symbol: newsSymbol, locked: false })}
          >
            <button
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2.5 bg-surface-2 border border-border rounded text-sm text-text-secondary hover:text-text-primary transition-colors min-h-[44px]"
            >
              <RefreshCw className="w-4 h-4" aria-hidden />
              Clear Lock
            </button>
          </ConfirmDialog>
        </div>
      </section>

      {/* Command history */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Recent Commands</h2>
        {commands.length === 0 ? (
          <p className="text-text-secondary text-sm">No commands sent yet.</p>
        ) : (
          <div className="space-y-2">
            {commands.map((cmd: Command) => (
              <div
                key={cmd.id}
                className="flex items-start gap-3 p-3 bg-surface-2 rounded border border-border/50 text-xs"
              >
                {statusIcon(cmd.status)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-text-primary">{cmd.type}</span>
                    <span className="text-text-secondary shrink-0">{timeAgo(cmd.created_at)}</span>
                  </div>
                  <p className={cn(
                    "mt-0.5",
                    cmd.status === "pending" ? "text-warning" :
                    cmd.status === "done"    ? "text-profit"  : "text-loss"
                  )}>
                    {CMD_NOTE[cmd.status]}
                  </p>
                  {cmd.result && (
                    <p className="text-text-secondary mt-0.5 truncate">{cmd.result}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
