"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Radio, Sparkles } from "lucide-react";

interface TradingViewLiveChartProps {
  symbol: "XAUUSD" | "BTCUSD";
  height?: number;
}

export function TradingViewLiveChart({
  symbol,
  height = 540,
}: TradingViewLiveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  const tvSymbol = symbol === "XAUUSD" ? "OANDA:XAUUSD" : "BINANCE:BTCUSDT";

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
      {/* Chart Top Badge */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#0C121C] border-b border-border text-[11px] text-text-secondary">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold text-text-primary">{symbol} H1 Real-Time TradingView Stream</span>
          <span className="px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] font-mono">
            Direct Exchange Feed
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline text-[10px] text-text-secondary">
            Zoom / Pan / Draw / Indicators Enabled
          </span>
        </div>
      </div>

      {/* Main Container */}
      <div
        ref={containerRef}
        className="w-full min-h-[480px]"
        style={{ height: `${height}px` }}
      >
        {!mounted && (
          <div className="w-full h-full flex items-center justify-center text-xs text-text-secondary font-mono">
            Loading Real-Time TradingView Chart...
          </div>
        )}
      </div>
    </div>
  );
}
