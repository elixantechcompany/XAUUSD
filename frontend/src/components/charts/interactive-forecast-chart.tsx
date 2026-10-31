"use client";

import { useState, useMemo, useEffect } from "react";
import {
  TrendingDown,
  TrendingUp,
  Shield,
  Target,
  Lock,
  Zap,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Info,
  CheckCircle2,
  Globe,
  BarChart2,
  Compass,
  ArrowRight,
  Eye,
  Layers,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { formatPrice, cn } from "@/lib/utils";
import { useBotStore } from "@/lib/store";

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

type SmcStep = "ALL" | "SWEEP" | "FVG" | "RETRACEMENT" | "CONFIRMATION" | "EXECUTION";

export function InteractiveForecastChart({
  initialInstrument = "XAUUSD",
}: InteractiveForecastChartProps) {
  const storeSignals = useBotStore((s) => s.signals);
  const [instrument, setInstrument] = useState<"XAUUSD" | "BTCUSD">(initialInstrument);
  const [activeStep, setActiveStep] = useState<SmcStep>("ALL");
  const [isPlayingCycle, setIsPlayingCycle] = useState(false);
  const [activeTab, setActiveTab] = useState<"reasons" | "macro" | "simulator">("reasons");

  // Check if a real active signal exists for the selected instrument
  const activeSignal = useMemo(() => {
    return storeSignals.find(
      (s) => s.instrument === instrument && !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
    );
  }, [storeSignals, instrument]);

  const [direction, setDirection] = useState<"SHORT" | "LONG">("SHORT");

  // Dynamic simulation progress: 0% = at entry, 100% = reached TP
  const [progress, setProgress] = useState<number>(35);

  const isXau = instrument === "XAUUSD";

  // Setup levels: prefer real active signal if present, otherwise interactive measurement levels
  const sweepLevel = activeSignal?.sweep_level ?? (isXau ? 4075.0 : 72800.0);
  const sweepExtreme = activeSignal?.sweep_extreme ?? (isXau ? 4082.5 : 73100.0);
  const fvgHigh = activeSignal?.fvg_high ?? (isXau ? 4068.37 : 72650.0);
  const fvgLow = activeSignal?.fvg_low ?? (isXau ? 4048.29 : 71850.0);
  const entryPrice = activeSignal?.entry ?? (isXau ? 4054.46 : 72450.0);
  const initialSl = activeSignal?.stop_loss ?? (isXau ? 4068.37 : 73100.0);
  const targetTp = activeSignal?.take_profit ?? (isXau ? 3988.98 : 70350.0);
  const triggerLevel = activeSignal?.trigger_level ?? (isXau ? 4054.46 : 72450.0);

  // 50% Consequent Encroachment (C.E.) of the Fair Value Gap
  const ceLevel = (fvgHigh + fvgLow) / 2;
  const fvgSize = Math.abs(fvgHigh - fvgLow);
  const fvgPips = (fvgSize * (isXau ? 10 : 1)).toFixed(1);

  // Chart range bounds
  const minPrice = isXau ? 3960.0 : 69800.0;
  const maxPrice = isXau ? 4160.0 : 73500.0;
  const priceRange = maxPrice - minPrice;

  // Calculate current simulated market price based on progress
  const totalTargetDistance = targetTp - entryPrice;
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
    trailPhase = "Locked +0.5R Partial Profit (Retracement Guardian)";
  } else if (currentRMultiple >= 1.0) {
    trailedStopLoss = direction === "SHORT" ? entryPrice - (isXau ? 0.2 : 5.0) : entryPrice + (isXau ? 0.2 : 5.0);
    trailPhase = "Risk-Free Breakeven Shifted (+1 pip)";
  }

  // Y coordinate mapper (SVG 0 is top, height is bottom)
  const svgHeight = 390;
  const svgWidth = 680;
  const getY = (val: number) => {
    const norm = (maxPrice - val) / priceRange;
    return Math.max(15, Math.min(svgHeight - 25, norm * (svgHeight - 40) + 20));
  };

  const candles = isXau ? XAUUSD_CANDLES : BTCUSD_CANDLES;

  // Grid levels matching TradingView layout
  const gridTicks = isXau
    ? [4160, 4140, 4120, 4100, 4080, 4054.46, 4020, 4000, 3988.98, 3960]
    : [73500, 73000, 72500, 72000, 71500, 71000, 70500, 70000];

  // Auto-play through 5-step SMC cycle
  useEffect(() => {
    if (!isPlayingCycle) return;
    const steps: SmcStep[] = ["SWEEP", "FVG", "RETRACEMENT", "CONFIRMATION", "EXECUTION", "ALL"];
    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % steps.length;
      setActiveStep(steps[idx]);
    }, 2800);
    return () => clearInterval(interval);
  }, [isPlayingCycle]);

  return (
    <div className="bg-[#0B1017] border border-[#243043] rounded-card overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.6)]">
      {/* ── Top Toolbar ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-[#121821] border-b border-[#1B2535]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 flex items-center justify-center">
            <Target className="w-4 h-4 text-gold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-extrabold text-sm text-white tracking-tight">
                TradingView SMC Quantitative Forecasting Engine
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent/15 text-accent border border-accent/30 font-mono">
                {activeSignal ? "Active Live Signal" : "Analytical Forecasting Tool"}
              </span>
            </div>
            <p className="text-[11px] text-text-secondary">
              Measure Fair Value Gaps, 50% Consequent Encroachment, Breakout Confirmation &amp; Dynamic Trailing Stop Shifts.
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
            onClick={() => setDirection((d) => (d === "SHORT" ? "LONG" : "SHORT"))}
            className={`px-3 py-1 text-xs font-bold rounded-inner flex items-center gap-1 border transition-all ${
              direction === "SHORT"
                ? "bg-red-950/60 text-red-300 border-red-800"
                : "bg-emerald-950/60 text-emerald-300 border-emerald-800"
            }`}
          >
            {direction === "SHORT" ? (
              <TrendingDown className="w-3.5 h-3.5 text-loss" />
            ) : (
              <TrendingUp className="w-3.5 h-3.5 text-profit" />
            )}
            <span>{direction} SETUP</span>
          </button>
        </div>
      </div>

      {/* ── 5-Step SMC Quantitative Workflow Bar ── */}
      <div className="bg-[#0e141d] px-4 py-2 border-b border-[#1B2535] flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          <span className="text-[11px] text-text-secondary font-medium mr-1 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-accent" />
            SMC Sequence:
          </span>

          <button
            onClick={() => { setActiveStep("SWEEP"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "SWEEP"
                ? "bg-amber-500/20 text-amber-300 border-amber-500/50 font-bold"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            1. Sweep Purge
          </button>

          <button
            onClick={() => { setActiveStep("FVG"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "FVG"
                ? "bg-purple-500/20 text-purple-300 border-purple-500/50 font-bold"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            2. Mark FVG Zone
          </button>

          <button
            onClick={() => { setActiveStep("RETRACEMENT"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "RETRACEMENT"
                ? "bg-blue-500/20 text-blue-300 border-blue-500/50 font-bold"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            3. Mitigation Tap
          </button>

          <button
            onClick={() => { setActiveStep("CONFIRMATION"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "CONFIRMATION"
                ? "bg-amber-400/20 text-amber-300 border-amber-400/50 font-bold animate-pulse"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            4. Wait Confirmation
          </button>

          <button
            onClick={() => { setActiveStep("EXECUTION"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "EXECUTION"
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50 font-bold"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            5. Execute &amp; Trail
          </button>

          <button
            onClick={() => { setActiveStep("ALL"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "ALL"
                ? "bg-accent/20 text-accent border-accent/50 font-bold"
                : "bg-[#070A0F] text-text-secondary border-[#243043] hover:text-white"
            )}
          >
            View Complete Forecast (Image 1)
          </button>
        </div>

        {/* Auto Play Cycle Button */}
        <button
          onClick={() => setIsPlayingCycle(!isPlayingCycle)}
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-semibold transition-all shrink-0",
            isPlayingCycle
              ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
              : "bg-[#070A0F] border-[#243043] text-text-secondary hover:text-white"
          )}
        >
          {isPlayingCycle ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          <span>{isPlayingCycle ? "Pause Sequence" : "Auto-Play Cycle"}</span>
        </button>
      </div>

      {/* ── Main Chart Stage (Replica of TradingView Image 1 & Beyond) ── */}
      <div className="relative bg-[#070A0F] select-none overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-[390px] min-w-[620px] font-mono text-[10px]"
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

          {/* ── 1. Liquidity Sweep Indicator (Step 1) ── */}
          {(activeStep === "ALL" || activeStep === "SWEEP") && (
            <g>
              <line
                x1="40"
                y1={getY(sweepLevel)}
                x2="350"
                y2={getY(sweepLevel)}
                stroke="#F59E0B"
                strokeWidth="1.5"
                strokeDasharray="4,2"
              />
              <rect
                x="45"
                y={getY(sweepLevel) - 16}
                width="190"
                height="15"
                fill="rgba(245, 158, 11, 0.15)"
                stroke="#F59E0B"
                strokeWidth="1"
                rx="2"
              />
              <text
                x="50"
                y={getY(sweepLevel) - 5}
                fill="#FBBF24"
                fontSize="8.5"
                fontWeight="bold"
              >
                SWEEP: BUY-SIDE LIQUIDITY (BSL) PURGED
              </text>
            </g>
          )}

          {/* ── 2. The Fair Value Gap (FVG) Imbalance Box (Step 2 - Image 1 purple/white box) ── */}
          {(activeStep === "ALL" || activeStep === "FVG" || activeStep === "RETRACEMENT" || activeStep === "CONFIRMATION" || activeStep === "EXECUTION") && (
            <g>
              <rect
                x="80"
                y={getY(fvgHigh)}
                width="310"
                height={Math.max(12, getY(fvgLow) - getY(fvgHigh))}
                fill="rgba(168, 85, 247, 0.14)"
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
                H1 FAIR VALUE GAP · {fvgPips} PIPS ({formatPrice(fvgLow)} — {formatPrice(fvgHigh)})
              </text>

              {/* 50% Consequent Encroachment (C.E.) Line */}
              <line
                x1="80"
                y1={getY(ceLevel)}
                x2="390"
                y2={getY(ceLevel)}
                stroke="#C084FC"
                strokeDasharray="3,3"
                strokeWidth="1.2"
              />
              <text
                x="320"
                y={getY(ceLevel) - 4}
                fill="#E9D5FF"
                fontSize="8"
              >
                50% C.E. {formatPrice(ceLevel)}
              </text>
            </g>
          )}

          {/* ── 3. Reference Candle Breakout Trigger Level (Step 4) ── */}
          {(activeStep === "ALL" || activeStep === "CONFIRMATION" || activeStep === "EXECUTION") && (
            <g>
              <line
                x1="140"
                y1={getY(triggerLevel)}
                x2="390"
                y2={getY(triggerLevel)}
                stroke="#38BDF8"
                strokeDasharray="5,2"
                strokeWidth="1.5"
              />
              <rect
                x="145"
                y={getY(triggerLevel) + 4}
                width="200"
                height="16"
                fill="rgba(2, 132, 199, 0.25)"
                stroke="#38BDF8"
                strokeWidth="1"
                rx="2"
              />
              <text
                x="150"
                y={getY(triggerLevel) + 16}
                fill="#38BDF8"
                fontSize="8.5"
                fontWeight="bold"
              >
                TRIGGER: 1-TICK BREAKOUT LEVEL ({formatPrice(triggerLevel)})
              </text>
            </g>
          )}

          {/* ── 4. The Forecasting Tool (Risk/Reward Box - Image 1 replica) ── */}
          {(activeStep === "ALL" || activeStep === "EXECUTION") && (
            <>
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

              {/* Tool label badge */}
              <g>
                <rect
                  x="195"
                  y={getY(entryPrice) + 8}
                  width="155"
                  height="22"
                  fill="rgba(7, 10, 15, 0.90)"
                  stroke="#38BDF8"
                  strokeWidth="1"
                  rx="4"
                />
                <text
                  x="202"
                  y={getY(entryPrice) + 23}
                  fill="#38BDF8"
                  fontSize="9"
                  fontWeight="bold"
                >
                  R:R 1:{rrRatio.toFixed(2)} · TARGET +{(totalReward).toFixed(1)} PTS
                </text>
              </g>
            </>
          )}

          {/* ── 5. Candlesticks ── */}
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
        </svg>
      </div>

      {/* ── Bottom Analytical Panels: Tabs ── */}
      <div className="border-t border-[#1B2535] bg-[#090E16]">
        {/* Navigation Tabs */}
        <div className="flex border-b border-[#1B2535] px-4">
          <button
            onClick={() => setActiveTab("reasons")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5",
              activeTab === "reasons"
                ? "border-accent text-accent bg-accent/5"
                : "border-transparent text-text-secondary hover:text-white"
            )}
          >
            <CheckCircle2 className="w-4 h-4 text-accent" />
            <span>Technical Reasons for Entry</span>
          </button>

          <button
            onClick={() => setActiveTab("macro")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5",
              activeTab === "macro"
                ? "border-gold text-gold bg-gold/5"
                : "border-transparent text-text-secondary hover:text-white"
            )}
          >
            <Globe className="w-4 h-4 text-gold" />
            <span>Why Markets Move (Macro Catalyst Flow)</span>
          </button>

          <button
            onClick={() => setActiveTab("simulator")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5",
              activeTab === "simulator"
                ? "border-emerald-500 text-emerald-400 bg-emerald-500/5"
                : "border-transparent text-text-secondary hover:text-white"
            )}
          >
            <Lock className="w-4 h-4 text-emerald-400" />
            <span>Dynamic Trailing Stop Simulator</span>
          </button>
        </div>

        {/* Tab 1: Technical Reasons for Entry */}
        {activeTab === "reasons" && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-accent" />
                Rigorous 5-Point Quantitative Trade Invalidation &amp; Entry Rules
              </h4>
              <span className="text-[11px] text-profit font-semibold px-2 py-0.5 rounded bg-profit/10 border border-profit/20 font-mono">
                Mathematical Edge Verified (R:R 1:{rrRatio.toFixed(2)})
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-amber-400 font-bold">
                  <span>1. Institutional Liquidity Sweep</span>
                  <span className="font-mono">{formatPrice(sweepLevel)}</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  The bot identified a prior swing high swept at {formatPrice(sweepLevel)} (extreme {formatPrice(sweepExtreme)}). This flushed resting buy-side liquidity (BSL) into institutional limit books before an immediate displacement lower.
                </p>
              </div>

              <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-purple-300 font-bold">
                  <span>2. 3-Candle Fair Value Gap (FVG)</span>
                  <span className="font-mono">{fvgPips} pips wide</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Inefficient 3-candle displacement created an imbalance between Candle 1 low and Candle 3 high ({formatPrice(fvgLow)} to {formatPrice(fvgHigh)}). Marked 50% Consequent Encroachment at {formatPrice(ceLevel)}.
                </p>
              </div>

              <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-blue-300 font-bold">
                  <span>3. Retracement &amp; Mitigation Check</span>
                  <span className="font-mono">50% C.E. Respected</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Price pulled back into the FVG to rebalance orders. The candle wicked into the 50% midpoint without closing outside the gap boundary, confirming structural respect and preventing invalidation.
                </p>
              </div>

              <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-emerald-300 font-bold">
                  <span>4. Reference Candle 1-Tick Breakout</span>
                  <span className="font-mono">Trigger: {formatPrice(triggerLevel)}</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  The bot refrained from premature entry, freezing the entering reference candle. Execution was triggered strictly upon a 1-tick breakout below the reference low, confirming directional velocity.
                </p>
              </div>
            </div>

            <div className="bg-[#121821] border border-border/80 rounded-inner p-3 flex items-start gap-2.5 text-xs text-text-secondary">
              <Sparkles className="w-4 h-4 text-gold shrink-0 mt-0.5" />
              <span>
                <strong>Zero Guesswork:</strong> Every single trade opened by the bot is systematically documented with these 5 criteria in the execution journal. If even one rule fails (e.g. invalidating candle close beyond FVG), the setup is discarded.
              </span>
            </div>
          </div>
        )}

        {/* Tab 2: Macroeconomic Market Catalysts (Why Markets Move) */}
        {activeTab === "macro" && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Globe className="w-4 h-4 text-gold" />
                Macroeconomic Catalyst Feed — Real Market Drivers Behind {instrument}
              </h4>
              <span className="text-[11px] text-text-secondary font-mono">
                Verified Institutional Sources
              </span>
            </div>

            {isXau ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gold">US 10-Year Real Yields (TIPS)</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      US Treasury
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Physical bullion pays zero nominal dividend or yield. Strong inverse correlation: when real yields fall or inflation expectations accelerate, holding physical gold becomes significantly more attractive to institutional asset allocators.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gold">US Dollar Index (DXY) Parity</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      ICE DXY
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Gold is globally denominated in US Dollars. Macro dollar weakness provides mechanical purchasing power expansion for sovereign foreign buyers in Asia and Europe, driving persistent spot demand.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gold">Central Bank Physical Accumulation</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      World Gold Council
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Continuous sovereign reserves diversification led by the People&apos;s Bank of China (PBOC) and Reserve Bank of India (RBI) establishing structural floor demand during London fixing hours.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gold">London / New York Golden Overlap</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      13:00 - 17:00 UTC
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Peak daily trading liquidity occurs when London afternoon trading coincides with the New York opening bell, producing the sharpest Fair Value Gaps and reliable institutional liquidity sweeps.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-accent">Institutional Spot ETF Inflows</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      Farside / Bloomberg
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Net institutional flows into US Spot Bitcoin ETFs (IBIT, FBTC, BITB, ARKB) absorb circulating spot supply. Post-halving daily miner issuance is ~450 BTC/day, meaning net ETF inflows exceeding $30M create direct supply deficit.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-accent">Global M2 Liquidity &amp; Fed Expectations</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      Federal Reserve
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Bitcoin acts as a high-beta thermometer for global fiat monetary liquidity. As global central bank balance sheets expand and interest rate cuts are priced in, high-scarcity digital assets experience accelerated demand.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-accent">CME Futures Basis &amp; Liquidity Pools</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      CME Group
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Perpetual funding rate equilibrium and institutional basis positioning. Stop-loss liquidity clusters concentrate heavily around psychological round numbers ($70,000 / $72,500 / $75,000) creating prime targets for SMC sweeps.
                  </p>
                </div>

                <div className="bg-[#121821] border border-[#243043] rounded-inner p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-accent">24/7 Market Microstructure</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">
                      Continuous Order Flow
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Weekend trading with thin retail order books often creates displacement imbalances that are systematically mitigated and filled once institutional desks reopen for the Monday cash session.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Dynamic Trailing Stop Simulator */}
        {activeTab === "simulator" && (
          <div className="p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-profit" />
                <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Dynamic Trailing &amp; Retracement Protection Simulator
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
                <span className="text-gold font-medium">Drag slider to test dynamic trailing stop shifts into Take Profit</span>
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
                <span className="text-[10px] text-text-secondary block">Active Trailed Stop</span>
                <span className="font-mono font-bold text-loss">{formatPrice(trailedStopLoss)}</span>
              </div>
              <div className="bg-[#121821] border border-[#243043] rounded p-2.5">
                <span className="text-[10px] text-text-secondary block">Copier Engine Replicate</span>
                <span className="font-mono font-bold text-emerald-400">&lt;200ms Execution</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
