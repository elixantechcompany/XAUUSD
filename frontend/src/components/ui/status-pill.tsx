import { cn, getBotStatus, STATUS_BG, STATUS_COLORS, timeAgo, type BotStatus } from "@/lib/utils";

interface StatusPillProps {
  lastHeartbeatTs: string | null | undefined;
  executionMode?: string;
  className?: string;
}

const STATUS_LABELS: Record<BotStatus, string> = {
  ONLINE:  "Bot Running",
  STALE:   "Stale",
  OFFLINE: "Offline",
  UNKNOWN: "Offline",
};

const STATUS_DOTS: Record<BotStatus, string> = {
  ONLINE:  "bg-profit animate-pulse",
  STALE:   "bg-warning",
  OFFLINE: "bg-loss",
  UNKNOWN: "bg-text-secondary",
};

export function StatusPill({ lastHeartbeatTs, executionMode, className }: StatusPillProps) {
  const status = getBotStatus(lastHeartbeatTs);
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium",
        STATUS_BG[status],
        className
      )}
      role="status"
      aria-label={`Bot status: ${STATUS_LABELS[status]}`}
    >
      <span className={cn("w-2 h-2 rounded-full", STATUS_DOTS[status])} aria-hidden />
      <span className={STATUS_COLORS[status]}>{STATUS_LABELS[status]}</span>
      {executionMode && (
        <span className="text-text-secondary text-xs uppercase tracking-wide">
          {executionMode}
        </span>
      )}
      {lastHeartbeatTs && status !== "ONLINE" && (
        <span className="text-text-secondary text-xs">{timeAgo(lastHeartbeatTs)}</span>
      )}
    </div>
  );
}
