import { cn } from "@/lib/utils";
import type { Direction } from "@/lib/supabase/types";
import { TrendingUp, TrendingDown } from "lucide-react";

interface DirectionBadgeProps {
  direction: Direction;
  size?: "sm" | "md";
  className?: string;
}

export function DirectionBadge({ direction, size = "md", className }: DirectionBadgeProps) {
  const isBull = direction === "BULLISH";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-semibold rounded",
        size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1",
        isBull
          ? "bg-profit/10 text-profit border border-profit/30"
          : "bg-loss/10 text-loss border border-loss/30",
        className
      )}
      aria-label={isBull ? "Buy / Long" : "Sell / Short"}
    >
      {isBull ? (
        <TrendingUp className="w-3 h-3" aria-hidden />
      ) : (
        <TrendingDown className="w-3 h-3" aria-hidden />
      )}
      {isBull ? "BUY" : "SELL"}
    </span>
  );
}
