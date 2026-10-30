import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a price with the right number of decimal places. */
export function formatPrice(price: number | null | undefined, digits = 2): string {
  if (price == null) return "—";
  return price.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Format P/L with sign, always 2 dp. */
export function formatPnl(pnl: number | null | undefined): string {
  if (pnl == null) return "—";
  const sign = pnl >= 0 ? "+" : "";
  return `${sign}${pnl.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format a percent. */
export function formatPct(pct: number | null | undefined, digits = 2): string {
  if (pct == null) return "—";
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(digits)}%`;
}

/** "2 minutes ago" style. */
export function timeAgo(ts: string | null | undefined): string {
  if (!ts) return "Unknown";
  return formatDistanceToNow(new Date(ts), { addSuffix: true });
}

/** UTC datetime string. */
export function utcDateTime(ts: string | null | undefined): string {
  if (!ts) return "Unknown";
  return format(new Date(ts), "yyyy-MM-dd HH:mm:ss") + " UTC";
}

/** Determine heartbeat status from last timestamp. */
export type BotStatus = "ONLINE" | "STALE" | "OFFLINE" | "UNKNOWN";

export function getBotStatus(lastTs: string | null | undefined): BotStatus {
  if (!lastTs) return "UNKNOWN";
  const ageSeconds = (Date.now() - new Date(lastTs).getTime()) / 1000;
  if (ageSeconds < 15)  return "ONLINE";
  if (ageSeconds < 60)  return "STALE";
  return "OFFLINE";
}

export const STATUS_COLORS: Record<BotStatus, string> = {
  ONLINE:  "text-profit",
  STALE:   "text-warning",
  OFFLINE: "text-loss",
  UNKNOWN: "text-text-secondary",
};

export const STATUS_BG: Record<BotStatus, string> = {
  ONLINE:  "bg-profit/10 border-profit/30",
  STALE:   "bg-warning/10 border-warning/30",
  OFFLINE: "bg-loss/10 border-loss/30",
  UNKNOWN: "bg-surface-2 border-border",
};

/** Map SetupState to a human-readable label. */
export const STATE_LABELS: Record<string, string> = {
  FVG_DETECTED:            "FVG Detected",
  SWEEP_CONFIRMED:         "Sweep Confirmed",
  WAITING_FOR_RETRACEMENT: "Waiting: Retracement",
  REFERENCE_CANDLE_SAVED:  "Reference Candle Saved",
  WAITING_FOR_GAP_EXIT:    "Waiting: Gap Exit",
  GAP_EXITED:              "Gap Exited",
  WAITING_FOR_TRIGGER:     "Waiting: Trigger Break",
  SIGNAL_READY:            "Signal Ready",
  RISK_CHECK:              "Risk Check",
  ORDER_PENDING:           "Order Pending",
  POSITION_OPEN:           "Position Open",
  CLOSED:                  "Closed",
  EXPIRED:                 "Expired",
  INVALIDATED:             "Invalidated",
  REJECTED:                "Rejected",
};

export const TERMINAL_STATES = new Set([
  "CLOSED", "EXPIRED", "INVALIDATED", "REJECTED",
]);

export const STATE_ORDER = [
  "FVG_DETECTED",
  "SWEEP_CONFIRMED",
  "WAITING_FOR_RETRACEMENT",
  "REFERENCE_CANDLE_SAVED",
  "WAITING_FOR_GAP_EXIT",
  "GAP_EXITED",
  "WAITING_FOR_TRIGGER",
  "SIGNAL_READY",
  "RISK_CHECK",
  "ORDER_PENDING",
  "POSITION_OPEN",
];

export function stateProgress(state: string): number {
  const idx = STATE_ORDER.indexOf(state);
  if (idx === -1) return 0;
  return Math.round(((idx + 1) / STATE_ORDER.length) * 100);
}

export function isActiveState(state: string): boolean {
  return !TERMINAL_STATES.has(state);
}
