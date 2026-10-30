"use client";

import { useState, useMemo } from "react";
import {
  TrendingDown,
  TrendingUp,
  Shield,
  Target,
  Maximize2,
  Lock,
  Zap,
  Play,
  RotateCcw,
  Sparkles,
  Info,
} from "lucide-react";
import { formatPrice } from "@/lib/utils";

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface InteractiveForecastChartProps {
  initialInstrument?: "XAUUSD" | "BTCUSD";
}

// XAUUSD historical candle cluster matching the user's TradingView screen (Image 1)
const XAUUSD_CANDLES: Candle[] = [
  { time: "28 08:00", open: 4030.1, high: 4045.2, low: 4022.0, close: 4040.5 },
  { time: "28 12:00", open: 4040.5, high: 4075.0, low: 4035.0, close: 4068.37 },
  { time: "28 16:00", open: 4068.37, high: 4082.5, low: 4058.0, close: 4072.0 },
  { time: "28 20:00", open: 4072.0, high: 4078.0, low: 4050.0, close: 4054.46 },
  { time: "29 00:00", open: 4054.46, high: 4058.0, low: 4032.0, close: 4038.2 },
  { time: "29 04:00", open: 4038.2, high: 4052.0, low: 4026.0, close: 4048.29 },
  { time: "29 08:00", open: 4048.29, high: 4060.0, low: 4030.0, close: 4034.0 },
  { time: "29 12:00", open: 4034.0, high: 4042.0, low: 4015.0, close: 4022.5 },
  { time: "29 16:00", open: 4022.5, high: 4030.0, low: 3995.0, close: 4004.0 },
  { time: "29 20:00", open: 4004.0, high: 4012.0, low: 3985.0, close: 3988.98 },
];

const BTCUSD_CANDLES: Candle[] = [
  { time: "28 08:00", open: 71200, high: 71950, low: 71100, close: 71800 },
  { time: "28 12:00", open: 71800, high: 72800, low: 71750, close: 72650 },
  { time: "28 16:00", open: 72650, high: 73100, low: 72300, close: 72450 },
  { time: "28 20:00", open: 72450, high: 72600, low: 71600, close: 71850 },
  { time: "29 00:00", open: 71850, high: 72100, low: 71400, close: 71600 },
  { time: "29 04:00", open: 71600, high: 72300, low: 71500, close: 72100 },
  { time: "29 08:00", open: 72100, high: 72500, low: 71800, close: 71900 },
  { time: "29 12:00", open: 71900, high: 72050, low: 71100, close: 71250 },
  { time: "29 16:00", open: 71250, high: 71400, low: 70600, close: 70800 },
  { time: "29 20:00", open: 70800, high: 71100, low: 70200, close: 70350 },
];

import { useBotStore } from "@/lib/store";

export function InteractiveForecastChart({
  initialInstrument = "XAUUSD",
}: InteractiveForecastChartProps) {
  const storeSignals = useBotStore((s) => s.signals);
  const [instrument, setInstrument] = useState<"XAUUSD" | "BTCUSD">(initialInstrument);

  // Check if a real active signal exists for the selected instrument
  const activeSignal = useMemo(() => {
    return storeSignals.find(
      (s) => s.instrument === instrument && !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
    );
  }, [storeSignals, instrument]);

  const [direction, setDirection] = useState<"SHORT" | "LONG">("SHORT");

  // Dynamic simulation progress: 0% = at entry, 100% = reached TP
  const [progress, setProgress] = useState<number>(35);

  // Setup levels: prefer real active signal if present, otherwise interactive measurement levels
  const isXau = instrument === "XAUUSD";
  const entryPrice = activeSignal?.entry ?? (isXau ? 4054.46 : 72450.0);
  const initialSl = activeSignal?.stop_loss ?? (isXau ? 4068.37 : 73100.0);
  const targetTp = activeSignal?.take_profit ?? (isXau ? 3988.98 : 70350.0);
  const fvgHigh = activeSignal?.fvg_high ?? (isXau ? 4068.37 : 72650.0);
  const fvgLow = activeSignal?.fvg_low ?? (isXau ? 4048.29 : 71850.0);

  // Chart range bounds
  const minPrice = isXau ? 3960.0 : 69800.0;
  const maxPrice = isXau ? 4160.0 : 73500.0;
  const priceRange = maxPrice - minPrice;

  // Calculate current simulated market price based on progress
  const totalTargetDistance = targetTp - entryPrice; // negative for short
  const currentPrice = entryPrice + totalTargetDistance * (progress / 100);

  // Risk & Reward calculations
  const initialRisk = Math.abs(entryPrice - initialSl);
  const totalReward = Math.abs(targetTp - entryPrice);
  const rrRatio = initialRisk > 0 ? totalReward / initialRisk : 2.0;

  // DYNAMIC TRAILING STOP LOSS (Aggressive Retracement Guardian)
  const currentProfitDistance = direction === "SHORT" ? entryPrice - currentPrice : currentPrice - entryPrice;
  const currentRMultiple = initialRisk > 0 ? currentProfitDistance / initialRisk : 0;

  let trailedStopLoss = initialSl;
  let trailPhase = "Initial Risk (1.0% Guard)";

  if (currentRMultiple >= 2.0) {
    trailedStopLoss = direction === "SHORT" ? entryPrice - initialRisk * 1.0 : entryPrice + initialRisk * 1.0;
    trailPhase = "Locked +1.0R Banked Profit (Protected)";
  } else if (currentRMultiple >= 1.5) {
    trailedStopLoss = direction === "SHORT" ? entryPrice - initialRisk * 0.5 : entryPrice + initialRisk * 0.5;
    trailPhase = "Locked +0.5R Partial Profit";
  } else if (currentRMultiple >= 1.0) {
    trailedStopLoss = direction === "SHORT" ? entryPrice - 0.2 : entryPrice + 0.2; // Breakeven + 1 pip
    trailPhase = "Risk-Free Breakeven Shifted";
  }

  // Y coordinate mapper (SVG 0 is top, height is bottom)
  const svgHeight = 380;
  const svgWidth = 680;
  const getY = (val: number) => {
    const norm = (maxPrice - val) / priceRange;
    return Math.max(15, Math.min(svgHeight - 25, norm * (svgHeight - 40) + 20));
  };

  const candles = isXau ? XAUUSD_CANDLES : BTCUSD_CANDLES;

  // Grid levels matching TradingView layout
  const gridTicks = isXau
    ? [4160, 4140, 4120, 4100, 4080, 4054.46, 4020, 4000, 3980, 3960]
    : [73500, 73000, 72500, 72000, 71500, 71000, 70500, 70000];

  return (
    <div className="bg-[#0D131C] border border-[#243043] rounded-card overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.6)]">
      {/* ── Top Toolbar ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#121821] border-b border-[#1B2535]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 flex items-center justify-center">
            <Target className="w-4 h-4 text-gold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-extrabold text-sm text-white tracking-tight">
                SMC Forecasting &amp; Measuring Tool
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent/15 text-accent border border-accent/30 font-mono">
                {activeSignal ? "Active Live Signal" : "Measuring Tool"}
              </span>
            </div>
            <p className="text-[11px] text-text-secondary">
              Measure Fair Value Gaps, Risk/Reward forecast zones &amp; dynamic trailing stop shifts.
            </p>
          </div>
        </div>

        {/* Controls: Symbol & Direction */}
        <div className="flex items-center gap-2">
          {/* Symbol Selector */}
          <div className="inline-flex rounded-inner bg-[#070A0F] p-0.5 border border-[#243043]">
            <button
              onClick={() => setInstrument("XAUUSD")}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                isXau ? "bg-gold text-black shadow font-bold" : "text-text-secondary hover:text-white"
              }`}
            >
              Gold (XAUUSD)
            </button>
            <button
              onClick={() => setInstrument("BTCUSD")}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                !isXau ? "bg-gold text-black shadow font-bold" : "text-text-secondary hover:text-white"
              }`}
            >
              Bitcoin (BTCUSD)
            </button>
          </div>

          {/* Direction */}
          <button
            onClick={() => setDirection(d => d === "SHORT" ? "LONG" : "SHORT")}
            className={`px-3 py-1 text-xs font-bold rounded-inner flex items-center gap-1 border transition-all ${
              direction === "SHORT"
                ? "bg-red-950/60 text-red-300 border-red-800"
                : "bg-emerald-950/60 text-emerald-300 border-emerald-800"
            }`}
          >
            {direction === "SHORT" ? <TrendingDown className="w-3.5 h-3.5 text-loss" /> : <TrendingUp className="w-3.5 h-3.5 text-profit" />}
            <span>{direction} POSITION</span>
          </button>
        </div>
      </div>

      {/* ── Main Chart Stage (Exact Visual Representation of Image 1) ── */}
      <div className="relative bg-[#070A0F] select-none overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-[380px] min-w-[620px] font-mono text-[10px]"
        >
          {/* Background grid lines */}
          {gridTicks.map((tick) => {
            const y = getY(tick);
            return (
              <g key={tick}>
                <line
                  x1="0"
                  y1={y}
                  x2={svgWidth - 75}
                  y2={y}
                  stroke="#1B2535"
                  strokeDasharray="3,3"
                  strokeWidth="1"
                />
                <text
                  x={svgWidth - 70}
                  y={y + 3}
                  fill="#64748B"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {formatPrice(tick)}
                </text>
              </g>
            );
          })}

          {/* Vertical Time Grid & Future Projection Line (matching Image 1) */}
          <line
            x1="410"
            y1="0"
            x2="410"
            y2={svgHeight - 20}
            stroke="#64748B"
            strokeDasharray="4,4"
            strokeWidth="1.2"
            opacity="0.6"
          />

          {/* ── 1. The Fair Value Gap (FVG) Imbalance Box (Image 1 purple/white box) ── */}
          <g>
            <rect
              x="80"
              y={getY(fvgHigh)}
              width="310"
              height={Math.max(12, getY(fvgLow) - getY(fvgHigh))}
              fill="rgba(168, 85, 247, 0.12)"
              stroke="#D8B4FE"
              strokeWidth="1.5"
              rx="2"
            />
            <text
              x="85"
              y={getY(fvgHigh) - 6}
              fill="#C084FC"
              fontSize="9"
              fontWeight="bold"
            >
              H1 FAIR VALUE GAP (IMBALANCE)
            </text>
          </g>

          {/* ── 2. The Forecasting Tool (Risk/Reward Box - Image 1 replica) ── */}
          {/* STOP LOSS ZONE (Red Shaded Box on Top for Short) */}
          <g>
            <rect
              x="185"
              y={getY(initialSl)}
              width="225"
              height={Math.max(4, getY(entryPrice) - getY(initialSl))}
              fill="rgba(239, 68, 68, 0.35)"
              stroke="#EF4444"
              strokeWidth="1.2"
            />
            {/* Stop Loss Price Tag on Right Axis */}
            <rect
              x={svgWidth - 75}
              y={getY(initialSl) - 8}
              width="72"
              height="16"
              fill="#EF4444"
              rx="2"
            />
            <text
              x={svgWidth - 70}
              y={getY(initialSl) + 4}
              fill="#FFFFFF"
              fontSize="9"
              fontWeight="bold"
            >
              SL {formatPrice(initialSl)}
            </text>
          </g>

          {/* TAKE PROFIT ZONE (Green Shaded Box on Bottom for Short) */}
          <g>
            <rect
              x="185"
              y={getY(entryPrice)}
              width="225"
              height={Math.max(4, getY(targetTp) - getY(entryPrice))}
              fill="rgba(16, 185, 129, 0.30)"
              stroke="#10B981"
              strokeWidth="1.2"
            />
            {/* Take Profit Price Tag on Right Axis */}
            <rect
              x={svgWidth - 75}
              y={getY(targetTp) - 8}
              width="72"
              height="16"
              fill="#10B981"
              rx="2"
            />
            <text
              x={svgWidth - 70}
              y={getY(targetTp) + 4}
              fill="#FFFFFF"
              fontSize="9"
              fontWeight="bold"
            >
              TP {formatPrice(targetTp)}
            </text>
          </g>

          {/* ENTRY LINE (White/Cyan horizontal divider) */}
          <line
            x1="185"
            y1={getY(entryPrice)}
            x2={svgWidth - 75}
            y2={getY(entryPrice)}
            stroke="#38BDF8"
            strokeWidth="1.8"
          />
          <rect
            x={svgWidth - 75}
            y={getY(entryPrice) - 8}
            width="72"
            height="16"
            fill="#0284C7"
            rx="2"
          />
          <text
            x={svgWidth - 70}
            y={getY(entryPrice) + 4}
            fill="#FFFFFF"
            fontSize="9"
            fontWeight="bold"
          >
            ENTRY {formatPrice(entryPrice)}
          </text>

          {/* DYNAMIC TRAILING STOP LINE (shifts as market drops into profit) */}
          {trailedStopLoss !== initialSl && (
            <g>
              <line
                x1="185"
                y1={getY(trailedStopLoss)}
                x2={svgWidth - 75}
                y2={getY(trailedStopLoss)}
                stroke="#F59E0B"
                strokeWidth="2"
                strokeDasharray="5,3"
              />
              <rect
                x={svgWidth - 75}
                y={getY(trailedStopLoss) - 8}
                width="72"
                height="16"
                fill="#F59E0B"
                rx="2"
              />
              <text
                x={svgWidth - 70}
                y={getY(trailedStopLoss) + 4}
                fill="#000000"
                fontSize="9"
                fontWeight="extrabold"
              >
                TRAILED {formatPrice(trailedStopLoss)}
              </text>
            </g>
          )}

          {/* ── 3. Candlesticks ── */}
          {candles.map((c, i) => {
            const x = 30 + i * 36;
            const openY = getY(c.open);
            const closeY = getY(c.close);
            const highY = getY(c.high);
            const lowY = getY(c.low);
            const isBull = c.close >= c.open;
            const candleTop = Math.min(openY, closeY);
            const candleHeight = Math.max(3, Math.abs(closeY - openY));

            return (
              <g key={i}>
                {/* Wick */}
                <line
                  x1={x}
                  y1={highY}
                  x2={x}
                  y2={lowY}
                  stroke={isBull ? "#10B981" : "#EF4444"}
                  strokeWidth="1.5"
                />
                {/* Body */}
                <rect
                  x={x - 6}
                  y={candleTop}
                  width="12"
                  height={candleHeight}
                  fill={isBull ? "#10B981" : "#EF4444"}
                  stroke={isBull ? "#059669" : "#DC2626"}
                  strokeWidth="1"
                  rx="1"
                />
              </g>
            );
          })}

          {/* Current Simulated Price Line */}
          <line
            x1="0"
            y1={getY(currentPrice)}
            x2={svgWidth - 75}
            y2={getY(currentPrice)}
            stroke="#EAB308"
            strokeWidth="1.2"
            strokeDasharray="2,2"
          />
          <circle
            cx={svgWidth - 85}
            cy={getY(currentPrice)}
            r="4"
            fill="#EAB308"
            className="animate-pulse"
          />

          {/* Tool label badge */}
          <g>
            <rect
              x="195"
              y={getY(entryPrice) + 8}
              width="140"
              height="20"
              fill="rgba(7, 10, 15, 0.85)"
              stroke="#38BDF8"
              strokeWidth="1"
              rx="4"
            />
            <text
              x="202"
              y={getY(entryPrice) + 22}
              fill="#38BDF8"
              fontSize="9"
              fontWeight="bold"
            >
              R:R 1:{rrRatio.toFixed(2)} · TARGET +{(totalReward).toFixed(1)} PTS
            </text>
          </g>
        </svg>
      </div>

      {/* ── Interactive Market Movement & Trailing SL Simulator ── */}
      <div className="p-4 bg-[#090E16] border-t border-[#1B2535] space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-profit" />
            <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
              Dynamic Trailing & Retracement Protection Simulator
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 rounded bg-[#121821] border border-[#243043] font-mono text-gold font-semibold">
              Live Price: {formatPrice(currentPrice)}
            </span>
            <span className="text-xs px-2.5 py-1 rounded bg-profit/15 text-profit border border-profit/30 font-semibold font-mono">
              {trailPhase}
            </span>
          </div>
        </div>

        {/* Slider to simulate market progression */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px] text-text-secondary">
            <span>Entry ({formatPrice(entryPrice)})</span>
            <span className="text-gold font-medium">Drag to simulate market movement into TP</span>
            <span>Take Profit ({formatPrice(targetTp)})</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={progress}
            onChange={(e) => setProgress(Number(e.target.value))}
            className="w-full accent-gold h-2 bg-[#1B2535] rounded cursor-pointer"
          />
        </div>

        {/* Key Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
          <div className="bg-[#121821] border border-[#243043] rounded p-2.5">
            <span className="text-[10px] text-text-secondary block">Risk/Reward</span>
            <span className="font-mono font-bold text-profit">1:{rrRatio.toFixed(2)} (Target)</span>
          </div>
          <div className="bg-[#121821] border border-[#243043] rounded p-2.5">
            <span className="text-[10px] text-text-secondary block">Current R-Multiple</span>
            <span className="font-mono font-bold text-gold">{currentRMultiple.toFixed(2)}R Progress</span>
          </div>
          <div className="bg-[#121821] border border-[#243043] rounded p-2.5">
            <span className="text-[10px] text-text-secondary block">Active Stop Loss</span>
            <span className="font-mono font-bold text-loss">{formatPrice(trailedStopLoss)}</span>
          </div>
          <div className="bg-[#121821] border border-[#243043] rounded p-2.5">
            <span className="text-[10px] text-text-secondary block">Fast Execution Engine</span>
            <span className="font-mono font-bold text-emerald-400">&lt;200ms Copier Sync</span>
          </div>
        </div>
      </div>
    </div>
  );
}
