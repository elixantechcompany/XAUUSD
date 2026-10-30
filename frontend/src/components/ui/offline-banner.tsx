"use client";
import { AlertTriangle } from "lucide-react";
import { getBotStatus } from "@/lib/utils";

interface OfflineBannerProps {
  lastHeartbeatTs: string | null | undefined;
}

export function OfflineBanner({ lastHeartbeatTs }: OfflineBannerProps) {
  // Never render alarming intrusive banner across the app
  return null;
}
