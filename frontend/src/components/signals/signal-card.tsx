"use client";
import { useState } from "react";
import { Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import type { Signal } from "@/lib/supabase/types";
import { DirectionBadge } from "@/components/ui/direction-badge";
import { StateProgress } from "@/components/ui/state-progress";
import { cn, formatPrice, formatPct, timeAgo, STATE_LABELS, TERMINAL_STATES } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
}

export function SignalCard({ signal }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const isActive   = !TERMINAL_STATES.has(signal.state);
  const isReady    = signal.state === "SIGNAL_READY" || signal.state === "POSITION_OPEN";
  const isTerminal = TERMINAL_STATES.has(signal.state);

  function copyTradeDetails() {
    const text = [
      `${signal.instrument} ${signal.direction}`,
      `Entry: ${signal.entry ?? "TBC"}`,
      `SL: ${signal.stop_loss ?? "TBC"}`,
      `TP: ${signal.take_profit ?? "TBC"}`,
      `R:R: 1:${signal.rr_ratio?.toFixed(2) ?? "?"}`,
      `State: ${STATE_LABELS[signal.state] ?? signal.state}`,
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <article
      className={cn(
        "bg-surface border rounded-card overflow-hidden transition-all",
        isReady   ? "border-accent/40"  :
        isTerminal && signal.state === "CLOSED" ? "border-profit/20" :
        isTerminal ? "border-border opacity-60" :
                   "border-border"
      )}
    >
      {/* ── Header ── */}
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn(
            "text-xs font-semibold px-2 py-0.5 rounded",
            signal.instrument === "XAUUSD"
              ? "bg-gold/10 text-gold border border-gold/30"
              : "bg-accent/10 text-accent border border-accent/30"
          )}>
            {signal.instrument}
          </span>
          <DirectionBadge direction={signal.direction} size="sm" />
          <span className="text-xs text-text-secondary">{signal.timeframe}</span>
          {signal.quality_grade && (
            <span className="text-xs px-1.5 py-0.5 bg-surface-2 border border-border rounded text-text-secondary">
              Grade {signal.quality_grade}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={copyTradeDetails}
            className="p-2 rounded hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
            aria-label="Copy trade details"
            title="Copy trade details"
          >
            {copied ? (
              <Check className="w-4 h-4 text-profit" aria-hidden />
            ) : (
              <Copy className="w-4 h-4" aria-hidden />
            )}
          </button>
          <button
            onClick={() => setExpanded(v => !v)}
            className="p-2 rounded hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors"
            aria-label={expanded ? "Collapse" : "Expand"}
            aria-expanded={expanded}
          >
            {expanded
              ? <ChevronUp className="w-4 h-4" aria-hidden />
              : <ChevronDown className="w-4 h-4" aria-hidden />
            }
          </button>
        </div>
      </div>

      {/* ── Key numbers ── */}
      <div className="px-4 pb-3 grid grid-cols-3 gap-3">
        <div>
          <p className="text-xs text-text-secondary mb-0.5">Entry</p>
          <p className="text-text-primary font-semibold tabular-nums text-sm">
            {signal.entry != null ? formatPrice(signal.entry) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-loss mb-0.5">Stop Loss</p>
          <p className="text-loss font-semibold tabular-nums text-sm">
            {signal.stop_loss != null ? formatPrice(signal.stop_loss) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-profit mb-0.5">Take Profit</p>
          <p className="text-profit font-semibold tabular-nums text-sm">
            {signal.take_profit != null ? formatPrice(signal.take_profit) : "—"}
          </p>
        </div>
      </div>

      {/* ── State + meta ── */}
      <div className="px-4 pb-3 flex items-center justify-between gap-2">
        <StateProgress currentState={signal.state} compact />
        <div className="flex items-center gap-3 text-xs text-text-secondary">
          {signal.rr_ratio != null && (
            <span>R:R 1:{signal.rr_ratio.toFixed(2)}</span>
          )}
          {signal.estimated_risk_usd != null && (
            <span>Risk ${signal.estimated_risk_usd.toFixed(2)}</span>
          )}
          <span>{timeAgo(signal.created_at)}</span>
        </div>
      </div>

      {/* ── Expanded detail ── */}
      {expanded && (
        <div className="border-t border-border bg-surface-2/50 p-4 space-y-4">

          {/* FVG + Sweep */}
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
              Setup Structure
            </h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div className="text-text-secondary">FVG Low</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.fvg_low)}</div>
              <div className="text-text-secondary">FVG High</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.fvg_high)}</div>
              <div className="text-text-secondary">Sweep Level</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.sweep_level)}</div>
              <div className="text-text-secondary">Sweep Extreme</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.sweep_extreme)}</div>
              <div className="text-text-secondary">Ref Candle High</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.ref_candle_high)}</div>
              <div className="text-text-secondary">Ref Candle Low</div>
              <div className="text-text-primary tabular-nums">{formatPrice(signal.ref_candle_low)}</div>
              <div className="text-text-secondary">Trigger Level</div>
              <div className="text-accent font-medium tabular-nums">{formatPrice(signal.trigger_level)}</div>
            </div>
          </section>

          {/* Full state progress */}
          <section>
            <StateProgress currentState={signal.state} />
          </section>

          {/* Rejection / reason */}
          {signal.rejection_reason && (
            <section>
              <h3 className="text-xs font-semibold text-loss uppercase tracking-wide mb-1">
                Rejection Reason
              </h3>
              <p className="text-xs text-text-secondary bg-loss/5 border border-loss/20 rounded p-2">
                {signal.rejection_reason}
              </p>
            </section>
          )}

          {/* Risk note */}
          <p className="text-xs text-text-secondary border-t border-border pt-3">
            Trading is risky. Signals are not guaranteed.
          </p>
        </div>
      )}
    </article>
  );
}
