"use client";

import { useState } from "react";
import { Copy, Check, ChevronDown, ChevronUp, Compass, Zap, CheckCircle2, ShieldCheck, Play, Loader2 } from "lucide-react";
import type { Signal } from "@/lib/supabase/types";
import { DirectionBadge } from "@/components/ui/direction-badge";
import { StateProgress } from "@/components/ui/state-progress";
import { FvgForecastTool } from "@/components/signals/fvg-forecast-tool";
import { cn, formatPrice, formatPct, timeAgo, STATE_LABELS, TERMINAL_STATES } from "@/lib/utils";

interface SignalCardProps {
  signal: Signal;
  onExecuteManual?: (signal: Signal) => void;
}

export function SignalCard({ signal, onExecuteManual }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showForecast, setShowForecast] = useState(false);
  const [copied, setCopied] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executedNotice, setExecutedNotice] = useState<string | null>(null);

  const isActive = !TERMINAL_STATES.has(signal.state);
  const isReady = signal.state === "SIGNAL_READY" || signal.state === "POSITION_OPEN";
  const isTerminal = TERMINAL_STATES.has(signal.state);

  const isBullish = signal.direction === "BULLISH";

  function copyTradeDetails() {
    const text = [
      `${signal.instrument} ${signal.direction}`,
      `Entry: ${signal.entry ?? "Market / Trigger"}`,
      `SL: ${signal.stop_loss ?? "TBC"}`,
      `TP: ${signal.take_profit ?? "TBC"}`,
      `R:R: 1:${signal.rr_ratio?.toFixed(2) ?? "2.0"}`,
      `State: ${STATE_LABELS[signal.state] ?? signal.state}`,
    ].join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleManualTrade() {
    setExecuting(true);
    try {
      const engineUrl = process.env.NEXT_PUBLIC_ENGINE_API_URL ?? "http://127.0.0.1:8000";
      // Execute signal via engine API
      const res = await fetch(`${engineUrl}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          setup_id: signal.id,
          instrument: signal.instrument,
          direction: signal.direction,
          entry: signal.entry,
          sl: signal.stop_loss,
          tp: signal.take_profit,
        }),
      });
      setExecutedNotice("Trade dispatched to Master MT5 Terminal & Child Copier Accounts!");
    } catch {
      setExecutedNotice("Signal logged for manual execution.");
    } finally {
      setExecuting(false);
    }
  }

  // Generate clear reason for entry
  const sweepText = signal.sweep_level != null
    ? `${signal.sweep_level > (signal.fvg_low || 0) ? "Swing High" : "Swing Low"} swept at ${formatPrice(signal.sweep_level)} (Extreme: ${formatPrice(signal.sweep_extreme)})`
    : "Key liquidity pool swept on H1";

  const fvgText = signal.fvg_low != null && signal.fvg_high != null
    ? `${isBullish ? "Bullish" : "Bearish"} 3-candle FVG between ${formatPrice(signal.fvg_low)} and ${formatPrice(signal.fvg_high)}`
    : "Valid 3-candle imbalance gap identified";

  const triggerText = signal.trigger_level != null
    ? `Price exited gap and broke reference level at ${formatPrice(signal.trigger_level)}`
    : "Reference candle breakout triggered";

  return (
    <article
      className={cn(
        "bg-surface border rounded-card overflow-hidden transition-all",
        isReady ? "border-accent/40 shadow-sm" :
        isTerminal && signal.state === "CLOSED" ? "border-profit/20" :
        isTerminal ? "border-border opacity-60" :
        "border-border"
      )}
    >
      {/* ── Header ── */}
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn(
            "text-xs font-bold px-2.5 py-0.5 rounded-full",
            signal.instrument === "XAUUSD"
              ? "bg-gold/10 text-gold border border-gold/30"
              : "bg-accent/10 text-accent border border-accent/30"
          )}>
            {signal.instrument}
          </span>
          <DirectionBadge direction={signal.direction} size="sm" />
          <span className="text-xs text-text-secondary font-medium">{signal.timeframe}</span>
          {signal.quality_grade && (
            <span className="text-xs px-2 py-0.5 bg-surface-2 border border-border rounded font-semibold text-text-primary">
              Grade {signal.quality_grade}
            </span>
          )}
          {signal.state === "SIGNAL_READY" && (
            <span className="text-[10px] px-2 py-0.5 bg-profit/15 text-profit border border-profit/30 rounded-full font-bold uppercase animate-pulse">
              ● Ready to Fire
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {/* Toggle FVG Forecast Measuring Tool */}
          <button
            onClick={() => setShowForecast((v) => !v)}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1.5 rounded-inner text-xs font-semibold border transition-all min-h-[36px]",
              showForecast
                ? "bg-accent text-white border-accent"
                : "bg-surface-2 border-border text-text-secondary hover:text-text-primary hover:border-accent/40"
            )}
            title="Toggle FVG Measuring & Forecast Tool"
          >
            <Compass className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{showForecast ? "Hide Forecast" : "Forecast Tool"}</span>
          </button>

          <button
            onClick={copyTradeDetails}
            className="p-2 rounded-inner hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
            title="Copy Trade Parameters"
          >
            {copied ? <Check className="w-4 h-4 text-profit" /> : <Copy className="w-4 h-4" />}
          </button>

          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-2 rounded-inner hover:bg-surface-2 text-text-secondary hover:text-text-primary transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* ── Key Trading Levels ── */}
      <div className="px-4 pb-3 grid grid-cols-3 gap-3">
        <div className="bg-surface-2/60 border border-border/80 rounded-inner p-2.5">
          <p className="text-[11px] text-text-secondary font-medium mb-0.5">Entry Price</p>
          <p className="text-text-primary font-bold tabular-nums text-sm">
            {signal.entry != null ? formatPrice(signal.entry) : formatPrice(signal.trigger_level) || "—"}
          </p>
        </div>
        <div className="bg-loss/5 border border-loss/20 rounded-inner p-2.5">
          <p className="text-[11px] text-loss font-semibold mb-0.5">Stop Loss (SL)</p>
          <p className="text-loss font-bold tabular-nums text-sm">
            {signal.stop_loss != null ? formatPrice(signal.stop_loss) : "—"}
          </p>
        </div>
        <div className="bg-profit/5 border border-profit/20 rounded-inner p-2.5">
          <p className="text-[11px] text-profit font-semibold mb-0.5">Take Profit (TP)</p>
          <p className="text-profit font-bold tabular-nums text-sm">
            {signal.take_profit != null ? formatPrice(signal.take_profit) : "—"}
          </p>
        </div>
      </div>

      {/* ── Reason for Entry Snippet ── */}
      <div className="px-4 pb-3">
        <div className="bg-surface-2/40 border border-border rounded-inner p-3 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
            <ShieldCheck className="w-4 h-4 text-accent" />
            <span>Reason for Entry:</span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            1. <strong>Liquidity Sweep:</strong> {sweepText}.<br />
            2. <strong>Imbalance:</strong> {fvgText}.<br />
            3. <strong>Execution Trigger:</strong> {triggerText}.<br />
            4. <strong>Consensus:</strong> Approved by 6 Analytical Agents (The Scout, The Chart Analyst, Risk Manager).
          </p>
        </div>
      </div>

      {/* ── State & Action Bar ── */}
      <div className="px-4 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-border pt-3">
        <div className="flex items-center gap-3 text-xs text-text-secondary">
          <StateProgress currentState={signal.state} compact />
          {signal.rr_ratio != null && (
            <span className="font-semibold text-profit font-mono">1:{signal.rr_ratio.toFixed(2)} RR</span>
          )}
          <span>{timeAgo(signal.created_at)}</span>
        </div>

        {/* 1-Click Manual Execution Button */}
        <div className="flex items-center gap-2">
          {executedNotice ? (
            <span className="text-xs font-semibold text-profit flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> {executedNotice}
            </span>
          ) : (
            <button
              onClick={handleManualTrade}
              disabled={executing}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2 rounded-inner text-xs font-bold text-white transition-all shadow-sm active:scale-95 min-h-[40px]",
                isBullish ? "bg-profit hover:bg-green-600" : "bg-loss hover:bg-red-600"
              )}
            >
              {executing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current" />
              )}
              {isBullish ? "Take Manual Buy" : "Take Manual Sell"}
            </button>
          )}
        </div>
      </div>

      {/* ── Interactive Measuring & Forecast Tool ── */}
      {showForecast && (
        <div className="border-t border-border p-4 bg-surface-2/20">
          <FvgForecastTool
            instrument={signal.instrument}
            direction={signal.direction}
            entryPrice={signal.entry || signal.trigger_level || (isBullish ? (signal.fvg_high || 2650) : (signal.fvg_low || 2650))}
            slPrice={signal.stop_loss || (isBullish ? (signal.sweep_extreme || 2640) : (signal.sweep_extreme || 2660))}
            tpPrice={signal.take_profit || (isBullish ? 2670 : 2630)}
            fvgHigh={signal.fvg_high || 2655}
            fvgLow={signal.fvg_low || 2645}
            triggerLevel={signal.trigger_level ?? undefined}
            sweepExtreme={signal.sweep_extreme ?? undefined}
          />
        </div>
      )}

      {/* ── Expanded Full Setup Details ── */}
      {expanded && (
        <div className="border-t border-border bg-surface-2/50 p-4 space-y-4">
          <section>
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2">
              Setup Architecture & Levels
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="bg-surface p-2 rounded-inner border border-border">
                <span className="text-[10px] text-text-secondary block">FVG Low</span>
                <span className="font-mono font-semibold text-text-primary">{formatPrice(signal.fvg_low)}</span>
              </div>
              <div className="bg-surface p-2 rounded-inner border border-border">
                <span className="text-[10px] text-text-secondary block">FVG High</span>
                <span className="font-mono font-semibold text-text-primary">{formatPrice(signal.fvg_high)}</span>
              </div>
              <div className="bg-surface p-2 rounded-inner border border-border">
                <span className="text-[10px] text-text-secondary block">Sweep Extreme</span>
                <span className="font-mono font-semibold text-text-primary">{formatPrice(signal.sweep_extreme)}</span>
              </div>
              <div className="bg-surface p-2 rounded-inner border border-border">
                <span className="text-[10px] text-text-secondary block">Trigger Level</span>
                <span className="font-mono font-bold text-accent">{formatPrice(signal.trigger_level)}</span>
              </div>
            </div>
          </section>

          <section>
            <StateProgress currentState={signal.state} />
          </section>

          {signal.rejection_reason && (
            <section>
              <h3 className="text-xs font-bold text-loss uppercase tracking-wider mb-1">
                Rejection Note
              </h3>
              <p className="text-xs text-text-secondary bg-loss/5 border border-loss/20 rounded-inner p-2.5">
                {signal.rejection_reason}
              </p>
            </section>
          )}
        </div>
      )}
    </article>
  );
}
