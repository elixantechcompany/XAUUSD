"use client";

import { useState, useEffect, type ReactNode } from "react";
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
  Lock,
  Unlock,
  AlertCircle,
} from "lucide-react";

// ── Typed icon map ─────────────────────────────────────────────────────────────
function statusIcon(status: CommandStatus): ReactNode {
  switch (status) {
    case "pending": return <Clock className="w-3.5 h-3.5 text-warning" aria-hidden />;
    case "done":    return <CheckCircle2 className="w-3.5 h-3.5 text-profit" aria-hidden />;
    case "failed":
    case "expired": return <XCircle className="w-3.5 h-3.5 text-loss" aria-hidden />;
  }
}

const CMD_NOTE: Record<CommandStatus, string> = {
  pending: "QUEUED — AWAITING ENGINE",
  done:    "Executed & acknowledged by engine",
  failed:  "Engine reported failure",
  expired: "Command expired before execution",
};

export default function ControlPage() {
  const heartbeat  = useBotStore((s) => s.heartbeat);
  const commands   = useBotStore((s) => s.recentCommands);
  const addCommand = useBotStore((s) => s.addCommand);

  const [sending, setSending]       = useState(false);
  const [newsSymbol, setNewsSym]    = useState<"XAUUSD" | "BTCUSD">("XAUUSD");
  const [error, setError]           = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Real-time track of locked symbols
  const [lockedSymbols, setLockedSymbols] = useState<Record<string, boolean>>({
    XAUUSD: false,
    BTCUSD: false,
  });

  const isOnline =
    heartbeat != null &&
    (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 < 60;

  // Initialize lock states from existing recent commands
  useEffect(() => {
    const lockStates: Record<string, boolean> = { XAUUSD: false, BTCUSD: false };
    // Find latest NEWS_LOCK command for each symbol
    for (const cmd of commands) {
      if (cmd.type === "NEWS_LOCK" && cmd.payload) {
        const sym = (cmd.payload as Record<string, unknown>).symbol as string;
        const isLocked = Boolean((cmd.payload as Record<string, unknown>).locked);
        if (sym && lockStates[sym] === undefined) {
          lockStates[sym] = isLocked;
        }
      }
    }
    setLockedSymbols((prev) => ({ ...prev, ...lockStates }));
  }, [commands]);

  async function dispatch(
    type: CommandType,
    payload: Record<string, unknown> = {}
  ): Promise<void> {
    setSending(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await sendCommand(type, payload);

      // Optimistically push to command feed
      const cmdId = "cmd_" + Date.now();
      addCommand({
        id: cmdId,
        type,
        payload,
        status: "done",
        created_at: new Date().toISOString(),
        result: type === "NEWS_LOCK"
          ? (payload.locked ? `News lockout active for ${payload.symbol}` : `News lockout cleared for ${payload.symbol}`)
          : `Command ${type} acknowledged`,
      });

      // Update UI feedback immediately
      if (type === "NEWS_LOCK") {
        const sym = payload.symbol as string;
        const isLock = Boolean(payload.locked);
        setLockedSymbols((prev) => ({ ...prev, [sym]: isLock }));
        setSuccessMsg(
          isLock
            ? `News Lockout ACTIVE: New entries for ${sym} are now blocked.`
            : `News Lockout CLEARED: Normal entries resumed for ${sym}.`
        );
      } else if (type === "PAUSE") {
        setSuccessMsg("Engine PAUSED: Entry signal generation suspended.");
      } else if (type === "RESUME") {
        setSuccessMsg("Engine RESUMED: Quantitative analysis and execution active.");
      } else if (type === "RESTART") {
        setSuccessMsg("Engine RESTARTED: Cooldowns cleared, linked accounts reloaded, scanning active.");
      } else if (type === "KILL") {
        setSuccessMsg("GLOBAL KILL SWITCH ENGAGED: All new submissions halted immediately.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send command");
    } finally {
      setSending(false);
    }
  }

  const isCurrentSymbolLocked = Boolean(lockedSymbols[newsSymbol]);

  return (
    <div className="space-y-6 max-w-2xl mx-auto pb-12">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Bot Control &amp; Risk Management</h1>
        <p className="text-xs text-text-secondary mt-1">
          Direct command terminal for manual lockouts, execution states, and emergency risk controls.
        </p>
      </div>

      {/* Success Notification Banner */}
      {successMsg && (
        <div className="bg-emerald-950/50 border border-emerald-800/60 rounded-card p-4 text-xs text-emerald-300 flex items-start gap-2.5 shadow-[0_0_20px_rgba(16,185,129,0.15)] animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium">{successMsg}</div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-red-950/50 border border-red-800/60 rounded-card p-4 text-xs text-red-300 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-loss shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
        </div>
      )}

      {/* Main Engine Controls */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Engine Operational State</h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <ConfirmDialog
            title="Pause new entries"
            description="The engine stops generating new entry signals. Open positions and their protective stops are not affected."
            confirmLabel="Pause Engine"
            onConfirm={() => dispatch("PAUSE")}
          >
            <button
              disabled={sending}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-surface-2 border border-border rounded font-semibold text-sm text-text-primary hover:bg-[#1A2230] transition-colors disabled:opacity-40 min-h-[44px]"
            >
              <Pause className="w-4 h-4 text-warning" aria-hidden />
              Pause Engine
            </button>
          </ConfirmDialog>

          <ConfirmDialog
            title="Resume monitoring"
            description="The engine will resume evaluating new SMC setups across all active sessions."
            confirmLabel="Resume Engine"
            onConfirm={() => dispatch("RESUME")}
          >
            <button
              disabled={sending}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-accent/10 border border-accent/30 rounded font-semibold text-sm text-accent hover:bg-accent/20 transition-colors disabled:opacity-40 min-h-[44px]"
            >
              <Play className="w-4 h-4 text-accent" aria-hidden />
              Resume Engine
            </button>
          </ConfirmDialog>

          <ConfirmDialog
            title="Restart Trading Engine"
            description="Re-synchronizes account balances from MT5, reloads all linked copier accounts, and resets scanning cooldowns immediately."
            confirmLabel="Restart Engine"
            onConfirm={() => dispatch("RESTART")}
          >
            <button
              disabled={sending}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-emerald-500/10 border border-emerald-500/30 rounded font-semibold text-sm text-emerald-400 hover:bg-emerald-500/20 transition-colors disabled:opacity-40 min-h-[44px]"
            >
              <RefreshCw className={cn("w-4 h-4 text-emerald-400", sending && "animate-spin")} aria-hidden />
              Restart Engine
            </button>
          </ConfirmDialog>
        </div>

        {/* Global Kill Switch */}
        <ConfirmDialog
          title="KILL SWITCH — Halt All Submissions"
          description="Immediately halts all order creation. Does not cancel broker-side protective stops on open positions. Only manual resume restores operation."
          confirmLabel="ENGAGE KILL SWITCH"
          danger
          requireTyped="KILL"
          onConfirm={() => dispatch("KILL")}
        >
          <button
            disabled={sending}
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-red-950/40 border border-red-800/60 rounded font-bold text-sm text-red-400 hover:bg-red-900/40 transition-colors disabled:opacity-40 min-h-[44px]"
          >
            <Zap className="w-4 h-4 text-red-400" aria-hidden />
            Emergency Kill Switch
          </button>
        </ConfirmDialog>
      </section>

      {/* Manual News Lockout */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-gold" />
            <h2 className="text-sm font-semibold text-text-primary">Manual News Lockout</h2>
          </div>
          <span className="text-xs text-text-secondary font-mono">
            High-Impact Protection
          </span>
        </div>
        <p className="text-xs text-text-secondary">
          Blocks new trade entries for the selected instrument during volatile economic events. Does not alter or remove existing protective stops.
        </p>

        {/* Symbol Selector with Live Status Badges */}
        <div className="flex gap-2">
          {(["XAUUSD", "BTCUSD"] as const).map((sym) => {
            const isLocked = Boolean(lockedSymbols[sym]);
            return (
              <button
                key={sym}
                onClick={() => setNewsSym(sym)}
                className={cn(
                  "flex items-center gap-2 px-3.5 py-2 rounded-inner text-xs font-semibold transition-all min-h-[40px] border",
                  newsSymbol === sym
                    ? "bg-accent text-white border-accent shadow-sm"
                    : "bg-surface-2 border-border text-text-secondary hover:text-text-primary"
                )}
              >
                <span>{sym}</span>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] font-bold font-mono",
                    isLocked
                      ? "bg-red-950 text-red-400 border border-red-800/80"
                      : "bg-emerald-950 text-emerald-400 border border-emerald-800/80"
                  )}
                >
                  {isLocked ? "LOCKED" : "ACTIVE"}
                </span>
              </button>
            );
          })}
        </div>

        {/* Current Selected Instrument Status Box */}
        <div className={cn(
          "p-3 rounded-inner border flex items-center justify-between text-xs",
          isCurrentSymbolLocked
            ? "bg-red-950/30 border-red-800/50 text-red-300"
            : "bg-emerald-950/30 border-emerald-800/50 text-emerald-300"
        )}>
          <div className="flex items-center gap-2">
            {isCurrentSymbolLocked ? (
              <Lock className="w-4 h-4 text-red-400" />
            ) : (
              <Unlock className="w-4 h-4 text-emerald-400" />
            )}
            <span>
              <strong>{newsSymbol}</strong> Status:{" "}
              {isCurrentSymbolLocked ? "LOCKED — New Entries Suspended" : "ACTIVE — Trading Allowed"}
            </span>
          </div>
          <span className="font-mono text-[11px]">
            {isCurrentSymbolLocked ? "Protection Active" : "Normal Flow"}
          </span>
        </div>

        {/* Action Buttons with Dynamic States */}
        <div className="flex gap-3 flex-wrap">
          <ConfirmDialog
            title={`Lock News Event — ${newsSymbol}`}
            description={`Suspend all new entries for ${newsSymbol}. Existing position stops will remain fully protected.`}
            confirmLabel="Confirm Lockout"
            onConfirm={() => dispatch("NEWS_LOCK", { symbol: newsSymbol, locked: true })}
          >
            <button
              disabled={sending || isCurrentSymbolLocked}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded text-xs font-bold transition-all min-h-[42px]",
                isCurrentSymbolLocked
                  ? "bg-surface-2 border border-border text-text-secondary opacity-60 cursor-not-allowed"
                  : "bg-warning/15 border border-warning/40 text-warning hover:bg-warning/25 shadow-sm"
              )}
            >
              <Lock className="w-3.5 h-3.5" aria-hidden />
              {isCurrentSymbolLocked ? `${newsSymbol} Already Locked` : `Lock ${newsSymbol}`}
            </button>
          </ConfirmDialog>

          <ConfirmDialog
            title={`Clear News Lock — ${newsSymbol}`}
            description={`Resume normal algorithmic entries for ${newsSymbol}.`}
            confirmLabel="Clear Lockout"
            onConfirm={() => dispatch("NEWS_LOCK", { symbol: newsSymbol, locked: false })}
          >
            <button
              disabled={sending || !isCurrentSymbolLocked}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded text-xs font-bold transition-all min-h-[42px]",
                !isCurrentSymbolLocked
                  ? "bg-surface-2 border border-border text-text-secondary opacity-60 cursor-not-allowed"
                  : "bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 hover:bg-emerald-900/40 shadow-sm"
              )}
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden />
              {!isCurrentSymbolLocked ? `${newsSymbol} Already Active` : `Clear Lock for ${newsSymbol}`}
            </button>
          </ConfirmDialog>
        </div>
      </section>

      {/* Command History */}
      <section className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text-primary">Recent Commands Log</h2>
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
                    <span className="font-semibold text-text-primary">{cmd.type}</span>
                    <span className="text-text-secondary shrink-0 font-mono text-[11px]">{timeAgo(cmd.created_at)}</span>
                  </div>
                  <p className={cn(
                    "mt-0.5 font-mono text-[11px]",
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
