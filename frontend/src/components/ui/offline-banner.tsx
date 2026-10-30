"use client";
import { AlertTriangle } from "lucide-react";
import { getBotStatus } from "@/lib/utils";

interface OfflineBannerProps {
  lastHeartbeatTs: string | null | undefined;
}

export function OfflineBanner({ lastHeartbeatTs }: OfflineBannerProps) {
  const status = getBotStatus(lastHeartbeatTs);
  if (status === "ONLINE") return null;

  const msg =
    status === "STALE"
      ? "Bot data is stale. Engine may be slow or reconnecting."
      : "Bot not reporting. New entries are not confirmed. Existing positions are protected only by broker-side stops verified as active.";

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 text-sm font-medium ${
        status === "STALE"
          ? "bg-warning/10 border-b border-warning/30 text-warning"
          : "bg-loss/10 border-b border-loss/30 text-loss"
      }`}
      role="alert"
      aria-live="assertive"
    >
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
      <span>{msg}</span>
    </div>
  );
}
