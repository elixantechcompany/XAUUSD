import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  subvalue?: ReactNode;
  icon?: ReactNode;
  className?: string;
  variant?: "default" | "profit" | "loss" | "warning";
}

const VARIANTS = {
  default: "",
  profit:  "border-profit/20",
  loss:    "border-loss/20",
  warning: "border-warning/20",
};

export function MetricCard({
  label, value, subvalue, icon, className, variant = "default",
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "bg-surface rounded-card border border-border p-4 flex flex-col gap-1",
        VARIANTS[variant],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-text-secondary text-xs uppercase tracking-wide font-medium">
          {label}
        </span>
        {icon && <span className="text-text-secondary">{icon}</span>}
      </div>
      <div className="text-text-primary font-semibold text-xl tabular-nums leading-tight">
        {value}
      </div>
      {subvalue && (
        <div className="text-text-secondary text-sm tabular-nums">{subvalue}</div>
      )}
    </div>
  );
}
