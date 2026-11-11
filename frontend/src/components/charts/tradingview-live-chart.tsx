"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Radio, Sparkles, Shield, Target, Lock, Compass, Eye, EyeOff } from "lucide-react";
import { formatPrice, cn } from "@/lib/utils";

interface TradingViewLiveChartProps {
  symbol: "XAUUSD" | "BTCUSD";
  height?: number;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  fvgLow?: number;
  fvgHigh?: number;
  trailedSl?: number;
  rrRatio?: number;
  direction?: string;
}

export function TradingViewLiveChart({
  symbol,
  height = 540,
  entryPrice,
  stopLoss,
  takeProfit,
  fvgLow,
  fvgHigh,
  trailedSl,
  rrRatio = 3.0,
  direction = "SHORT",
}: TradingViewLiveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [showForecastOverlay, setShowForecastOverlay] = useState(true);

  const isXau = symbol === "XAUUSD";
  const tvSymbol = isXau ? "OANDA:XAUUSD" : "BINANCE:BTCUSDT";

  // Fallbacks if not explicitly provided
  const effEntry = entryPrice ?? (isXau ? 3875.70 : 77262.58);
  const effSl = stopLoss ?? (isXau ? 3885.54 : 77430.27);
  const effTp = takeProfit ?? (isXau ? 3846.18 : 76759.51);
  const slDistance = Math.abs(effEntry - effSl);
  const tpDistance = Math.abs(effTp - effEntry);
  const pipMultiplier = isXau ? 10 : 1;
  const slPips = (slDistance * pipMultiplier).toFixed(1);
  const tpPips = (tpDistance * pipMultiplier).toFixed(1);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !containerRef.current) return;

    // Clear previous widget
    const container = containerRef.current;
    container.innerHTML = "";

    const widgetId = `tv_widget_${symbol}_${Math.random().toString(36).substring(2, 7)}`;
    const widgetDiv = document.createElement("div");
    widgetDiv.id = widgetId;
    widgetDiv.style.width = "100%";
    widgetDiv.style.height = `${height}px`;
    container.appendChild(widgetDiv);

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/tv.js";
    script.type = "text/javascript";
    script.async = true;
    script.onload = () => {
      if (typeof (window as unknown as { TradingView?: { widget: new (opts: Record<string, unknown>) => unknown } }).TradingView !== "undefined") {
        new (window as unknown as { TradingView: { widget: new (opts: Record<string, unknown>) => unknown } }).TradingView.widget({
          autosize: true,
          symbol: tvSymbol,
          interval: "60",
          timezone: "Etc/UTC",
          theme: "dark",
          style: "1", // 1 = Candlesticks
          locale: "en",
          toolbar_bg: "#070A0F",
          enable_publishing: false,
          allow_symbol_change: false,
          container_id: widgetId,
          hide_side_toolbar: false,
          studies: [
            "STD;RSI",
          ],
        });
      }
    };
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [symbol, height, mounted, tvSymbol]);

  return (
    <div className="w-full bg-[#070A0F] border border-border rounded-b-card overflow-hidden relative">
      {/* Chart Top Badge & Forecasting Control Bar */}
      <div className="flex flex-wrap items-center justify-between px-3 py-2 bg-[#0C121C] border-b border-border text-[11px] text-text-secondary gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold text-text-primary">{symbol} H1 Real-Time TradingView Stream</span>
          <span className="px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] font-mono">
            Direct Exchange Feed
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle Forecast Tool Overlays */}
          <button
            type="button"
            onClick={() => setShowForecastOverlay(!showForecastOverlay)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-border text-text-primary text-[11px] font-semibold hover:border-accent/50 transition-colors"
          >
            <Compass className="w-3.5 h-3.5 text-accent" />
            <span>{showForecastOverlay ? "Hide SL/TP Overlay" : "Show SL/TP Overlay"}</span>
          </button>
        </div>
      </div>

      {/* Floating Forecasting Tool HUD — Stop Loss & Take Profit Levels */}
      {showForecastOverlay && (
        <div className="bg-surface-2/95 border-b border-border px-3 py-2 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1">
              <Compass className="w-3.5 h-3.5 text-accent" /> Forecasting Markers:
            </span>

            {/* Entry Marker */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-border text-[11px]">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span className="text-text-secondary font-medium">Entry:</span>
              <strong className="text-text-primary font-mono">{formatPrice(effEntry)}</strong>
            </div>

            {/* Stop Loss Marker */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-loss/15 border border-loss/30 text-[11px]">
              <Shield className="w-3.5 h-3.5 text-loss" />
              <span className="text-loss/90 font-medium">Stop Loss:</span>
              <strong className="text-loss font-mono">{formatPrice(effSl)}</strong>
              <span className="text-[10px] text-loss/80 font-mono">(-{slPips} pips)</span>
            </div>

            {/* Take Profit Marker (1:3 RR) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-profit/15 border border-profit/30 text-[11px]">
              <Target className="w-3.5 h-3.5 text-profit" />
              <span className="text-profit/90 font-medium">1:{rrRatio.toFixed(1)} RR Target:</span>
              <strong className="text-profit font-mono">{formatPrice(effTp)}</strong>
              <span className="text-[10px] text-profit/80 font-mono">(+{tpPips} pips)</span>
            </div>

            {/* Trailed SL / Breakeven Milestone */}
            {trailedSl != null && trailedSl !== effSl && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/15 border border-amber-500/30 text-[11px]">
                <Lock className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-amber-300 font-medium">Trailed SL:</span>
                <strong className="text-amber-400 font-mono">{formatPrice(trailedSl)}</strong>
                <span className="text-[10px] text-amber-300/80 font-mono">(Breakeven Guard)</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-text-secondary font-mono">
            <span>Aggressive Retracement Breakeven:</span>
            <span className="text-emerald-400 font-bold">ARMED</span>
          </div>
        </div>
      )}

      {/* Main TradingView Container */}
      <div
        ref={containerRef}
        className="w-full min-h-[480px]"
        style={{ height: `${height}px` }}
      >
        {!mounted && (
          <div className="w-full h-full flex items-center justify-center text-xs text-text-secondary font-mono">
            Loading Real-Time TradingView Chart with Forecast Markers...
          </div>
        )}
      </div>
    </div>
  );
}
