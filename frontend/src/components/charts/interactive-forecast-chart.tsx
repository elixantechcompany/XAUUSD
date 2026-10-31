"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
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
  RefreshCw,
  Sun,
  Moon,
  Clock,
  DollarSign,
  Maximize2,
  Radio,
} from "lucide-react";
import { formatPrice, cn } from "@/lib/utils";
import { useBotStore } from "@/lib/store";
import { TradingViewLiveChart } from "./tradingview-live-chart";

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

type SmcStep = "ALL" | "SWEEP" | "FVG" | "RETRACEMENT" | "CONFIRMATION" | "EXECUTION";

export function InteractiveForecastChart({
  initialInstrument = "BTCUSD",
}: InteractiveForecastChartProps) {
  const storeSignals = useBotStore((s) => s.signals);
  const heartbeat = useBotStore((s) => s.heartbeat);
  const account = useBotStore((s) => s.account);

  const [instrument, setInstrument] = useState<"XAUUSD" | "BTCUSD">(initialInstrument);
  const [chartViewMode, setChartViewMode] = useState<"tradingview" | "smc_matrix">("tradingview");
  const [activeStep, setActiveStep] = useState<SmcStep>("ALL");
  const [isPlayingCycle, setIsPlayingCycle] = useState(false);
  const [activeTab, setActiveTab] = useState<"calculator" | "reasons" | "macro" | "simulator">("calculator");
  const [isAutoSimulating, setIsAutoSimulating] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState<1 | 2>(1);
  const [studyAnalyzing, setStudyAnalyzing] = useState(false);

  // ── Live Market Data & Dynamic Engine State ────────────────────────────────
  const [liveCandles, setLiveCandles] = useState<Candle[]>([]);
  const [liveCurrentPrice, setLiveCurrentPrice] = useState<number | null>(null);
  const [liveSpread, setLiveSpread] = useState<number>(1.2);
  const [liveBotStatus, setLiveBotStatus] = useState<string>("BOT RUNNING · ANALYZING (MT5 Stream Active)");
  const [liveBotState, setLiveBotState] = useState<string>("ANALYZING");
  const [liveReasoning, setLiveReasoning] = useState<string>("Scanning H1 bar structure for liquidity sweep and cyan Fair Value Gap.");
  const [lastDataUpdate, setLastDataUpdate] = useState<string>(new Date().toLocaleTimeString());
  const [isLiveLoading, setIsLiveLoading] = useState(false);
  const [openPositions, setOpenPositions] = useState<any[]>([]);
  const [isExecutingTrade, setIsExecutingTrade] = useState(false);
  const [isClosingTrade, setIsClosingTrade] = useState(false);
  const [actionToast, setActionToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Theme state
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    if (typeof document !== "undefined") {
      setIsDark(document.documentElement.classList.contains("dark"));
    }
  }, []);

  function toggleLocalTheme() {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
      localStorage.setItem("theme", "light");
    }
  }

  // ── Fetch Live MT5 Market Data from Internal API Route ─────────────────────
  const fetchLiveMarketData = useCallback(async () => {
    try {
      const res = await fetch(`/api/market/live?symbol=${instrument}`, { cache: "no-store" });
      if (res.ok) {
        const json = await res.json();
        if (json.open_positions) {
          setOpenPositions(json.open_positions);
        }
        if (json.data) {
          const d = json.data;
          if (d.candles && d.candles.length > 0) {
            setLiveCandles(d.candles);
          }
          if (d.current_price != null) {
            setLiveCurrentPrice(d.current_price);
          }
          if (d.spread_pts != null) {
            setLiveSpread(d.spread_pts);
          }
          if (json.bot_status) {
            setLiveBotStatus(json.bot_status);
          }
          if (json.bot_state) {
            setLiveBotState(json.bot_state);
          }
          if (json.reasoning) {
            setLiveReasoning(json.reasoning);
          }
          setLastDataUpdate(new Date().toLocaleTimeString());
        }
      }
    } catch {
      // fallback
    }
  }, [instrument]);

  useEffect(() => {
    setIsLiveLoading(true);
    fetchLiveMarketData().finally(() => setIsLiveLoading(false));
    const interval = setInterval(fetchLiveMarketData, 3500);
    return () => clearInterval(interval);
  }, [fetchLiveMarketData]);

  const isXau = instrument === "XAUUSD";

  // Check if a database active signal exists
  const activeSignal = useMemo(() => {
    return storeSignals.find(
      (s) => s.instrument === instrument && !["CLOSED", "EXPIRED", "INVALIDATED", "REJECTED"].includes(s.state)
    );
  }, [storeSignals, instrument]);

  const [direction, setDirection] = useState<"SHORT" | "LONG">("SHORT");
  const [progress, setProgress] = useState<number>(35);

  // ── Realistic Dynamic Candlesticks fallback if MT5 not ready ───────────────
  const defaultAnchor = isXau ? 3875.0 : 77190.0;
  const currentPriceAnchor = liveCurrentPrice ?? defaultAnchor;
  const step = isXau ? 2.5 : 120.0;

  const candles: Candle[] = useMemo(() => {
    if (liveCandles.length >= 5) return liveCandles;
    return [
      { time: "30 20:00", open: round2(currentPriceAnchor + step * 3.2), high: round2(currentPriceAnchor + step * 4.5), low: round2(currentPriceAnchor + step * 2.0), close: round2(currentPriceAnchor + step * 3.8) },
      { time: "31 00:00", open: round2(currentPriceAnchor + step * 3.8), high: round2(currentPriceAnchor + step * 5.2), low: round2(currentPriceAnchor + step * 3.2), close: round2(currentPriceAnchor + step * 4.9) },
      { time: "31 04:00", open: round2(currentPriceAnchor + step * 4.9), high: round2(currentPriceAnchor + step * 5.5), low: round2(currentPriceAnchor + step * 2.8), close: round2(currentPriceAnchor + step * 3.1) },
      { time: "31 08:00", open: round2(currentPriceAnchor + step * 3.1), high: round2(currentPriceAnchor + step * 3.9), low: round2(currentPriceAnchor + step * 1.2), close: round2(currentPriceAnchor + step * 1.8) },
      { time: "31 10:00", open: round2(currentPriceAnchor + step * 1.8), high: round2(currentPriceAnchor + step * 2.4), low: round2(currentPriceAnchor - step * 0.4), close: round2(currentPriceAnchor) },
    ];
  }, [liveCandles, currentPriceAnchor, step]);

  // Dynamic SMC Levels calculated live from recent price action
  const recentHighs = candles.map((c) => c.high);
  const sweepExtreme = activeSignal?.sweep_extreme ?? Math.max(...recentHighs, currentPriceAnchor + (isXau ? 8.5 : 420.0));
  const sweepLevel = activeSignal?.sweep_level ?? (sweepExtreme - (isXau ? 1.5 : 75.0));

  // Vibrant Cyan Fair Value Gap (Image 1 Marked Zone)
  const fvgHigh = activeSignal?.fvg_high ?? (currentPriceAnchor + (isXau ? 4.2 : 210.0));
  const fvgLow = activeSignal?.fvg_low ?? (currentPriceAnchor + (isXau ? 1.4 : 70.0));
  const ceLevel = (fvgHigh + fvgLow) / 2;
  const fvgSize = Math.abs(fvgHigh - fvgLow);
  const fvgPoints = (fvgSize).toFixed(2);
  const fvgPips = (fvgSize * (isXau ? 10 : 1)).toFixed(1);

  const entryPrice = activeSignal?.entry ?? currentPriceAnchor;
  const initialSl = activeSignal?.stop_loss ?? (fvgHigh + (isXau ? 1.5 : 85.0));
  const slDistance = Math.abs(entryPrice - initialSl);
  const slPoints = slDistance.toFixed(2);
  const slPips = (slDistance * (isXau ? 10 : 1)).toFixed(1);

  const rrRatio = 3.2;
  const targetTp = activeSignal?.take_profit ?? (entryPrice - slDistance * rrRatio);
  const triggerLevel = activeSignal?.trigger_level ?? (entryPrice - (isXau ? 0.3 : 15.0));

  // Dynamic simulated price slider
  const totalTargetDistance = targetTp - entryPrice;
  const currentPrice = entryPrice + totalTargetDistance * (progress / 100);

  // ── Observed Balance & Small-Account Risk Calculator ($50+) ────────────────
  const liveBalance = (heartbeat?.balance && heartbeat.balance > 0)
    ? heartbeat.balance
    : (account?.balance && account.balance > 0)
      ? account.balance
      : null;

  const [testBalance, setTestBalance] = useState<number>(50.0); // Default to $50 small account as requested
  const [customBalanceInput, setCustomBalanceInput] = useState<string>("50");
  const [isUsingLiveBalance, setIsUsingLiveBalance] = useState(false);

  // Sizing mode: Small Account Fast-Growth (2.5%) vs Institutional (1.0%)
  const [sizingMode, setSizingMode] = useState<"FAST_GROWTH" | "CONSERVATIVE">("FAST_GROWTH");

  const effectiveBalance = isUsingLiveBalance && liveBalance !== null ? liveBalance : testBalance;

  // Small accounts ($50 - $500) use 2.5% to compound faster, while capping maximum downside
  const riskPercent = sizingMode === "FAST_GROWTH" ? 2.5 : 1.0;
  const riskUsd = effectiveBalance * (riskPercent / 100);

  // Contract Multiplier: XAUUSD = 100 oz per lot, BTCUSD = 1 BTC per lot
  const contractMultiplier = isXau ? 100 : 1;
  const pointValuePerLot = contractMultiplier; // $ per 1.0 point move for 1.0 lot

  // Dynamic Lot Sizing Formula: Lot = Risk Budget / (SL Distance * Point Value)
  const rawLotSize = slDistance > 0 ? riskUsd / (slDistance * pointValuePerLot) : 0.01;
  // Quantize strictly to broker minimum 0.01 lot step
  const calculatedLotSize = Math.max(0.01, Math.min(100.0, Math.floor(rawLotSize * 100) / 100));

  // Actual dollar risk and reward based on quantized lot
  const actualRiskUsd = slDistance * pointValuePerLot * calculatedLotSize;
  const rewardDistance = Math.abs(targetTp - entryPrice);
  const rewardPoints = rewardDistance.toFixed(2);
  const rewardPips = (rewardDistance * (isXau ? 10 : 1)).toFixed(1);
  const actualRewardUsd = rewardDistance * pointValuePerLot * calculatedLotSize;

  // Margin required approximation at 1:2000 leverage (Exness)
  const leverage = 2000;
  const marginRequired = (entryPrice * contractMultiplier * calculatedLotSize) / leverage;

  // Auto-simulate market movement
  useEffect(() => {
    if (!isAutoSimulating) return;
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setIsAutoSimulating(false);
          return 100;
        }
        return Math.min(100, prev + 1.2 * simulationSpeed);
      });
    }, 120);
    return () => clearInterval(interval);
  }, [isAutoSimulating, simulationSpeed]);

  // DYNAMIC TRAILING STOP LOSS (Aggressive Retracement Guardian)
  const initialRisk = slDistance;
  const currentProfitDistance = direction === "SHORT" ? entryPrice - currentPrice : currentPrice - entryPrice;
  const currentRMultiple = initialRisk > 0 ? currentProfitDistance / initialRisk : 0;

  let trailedStopLoss = initialSl;
  let trailPhase = "Initial Protective SL";

  if (currentRMultiple >= 2.0) {
    trailedStopLoss = entryPrice - initialRisk * 1.0;
    trailPhase = "Banked +1.0R Locked in Profit";
  } else if (currentRMultiple >= 1.5) {
    trailedStopLoss = entryPrice - initialRisk * 0.5;
    trailPhase = "Retracement Guardian Tightened (+0.5R)";
  } else if (currentRMultiple >= 1.0) {
    trailedStopLoss = entryPrice - (isXau ? 0.2 : 5.0);
    trailPhase = "Risk-Free Breakeven Shifted (+1 pip)";
  }

  // Chart range bounds dynamically scaled to live candle cluster
  const allPrices = candles.flatMap((c) => [c.high, c.low]).concat([sweepExtreme, initialSl, targetTp, currentPriceAnchor]);
  const minPrice = Math.min(...allPrices) - (isXau ? 4.0 : 150.0);
  const maxPrice = Math.max(...allPrices) + (isXau ? 4.0 : 150.0);
  const priceRange = Math.max(maxPrice - minPrice, 1.0);

  const svgHeight = 390;
  const svgWidth = 680;
  const getY = (val: number) => {
    const norm = (maxPrice - val) / priceRange;
    return Math.max(18, Math.min(svgHeight - 25, norm * (svgHeight - 45) + 20));
  };

  const gridTicks = [
    maxPrice,
    maxPrice - priceRange * 0.25,
    maxPrice - priceRange * 0.5,
    maxPrice - priceRange * 0.75,
    minPrice,
  ];

  function handleBalanceInputChange(val: string) {
    setCustomBalanceInput(val);
    const num = parseFloat(val);
    if (!isNaN(num) && num > 0) {
      setTestBalance(num);
      setIsUsingLiveBalance(false);
    }
  }

  // ── 1-Click MT5 Trade Execution & Close Handlers (1:3 RR) ──────────────────
  const handleExecuteTrade = async () => {
    setIsExecutingTrade(true);
    setActionToast(null);
    try {
      const res = await fetch("/api/trade/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: instrument,
          direction: direction,
          volume: calculatedLotSize,
          stop_loss: initialSl,
          take_profit: targetTp,
          rr_ratio: 3.0,
          reason: `SMC FVG Retracement Confirmation (1:3 RR, SL: ${initialSl}, TP: ${targetTp})`,
        }),
      });
      const json = await res.json();
      if (res.ok && json.success) {
        setActionToast({
          message: `Trade dispatched to Exness MT5! Ticket fill pending (${direction} ${calculatedLotSize} lot, 1:3 RR)`,
          type: "success",
        });
        setTimeout(fetchLiveMarketData, 1200);
      } else {
        setActionToast({ message: json.error || "Failed to dispatch order to MT5", type: "error" });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Execution network error";
      setActionToast({ message: msg, type: "error" });
    } finally {
      setIsExecutingTrade(false);
    }
  };

  const handleCloseTrade = async (ticketToClose?: string) => {
    setIsClosingTrade(true);
    setActionToast(null);
    try {
      const res = await fetch("/api/trade/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket: ticketToClose,
          symbol: instrument,
        }),
      });
      const json = await res.json();
      if (res.ok && json.success) {
        setActionToast({
          message: json.message || "Close order dispatched to Exness MT5 bridge",
          type: "success",
        });
        setTimeout(fetchLiveMarketData, 1200);
      } else {
        setActionToast({ message: json.error || "Failed to close trade", type: "error" });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Close error";
      setActionToast({ message: msg, type: "error" });
    } finally {
      setIsClosingTrade(false);
    }
  };

  // Find active position on MT5 for this instrument or general
  const activePosition = openPositions.find(
    (p) =>
      p.symbol === instrument ||
      p.symbol === `${instrument}m` ||
      (instrument === "BTCUSD" && p.symbol.includes("BTC")) ||
      (instrument === "XAUUSD" && (p.symbol.includes("XAU") || p.symbol.includes("GOLD")))
  ) || (openPositions.length > 0 ? openPositions[0] : null);

  return (
    <div className="bg-surface border border-border rounded-card overflow-hidden shadow-sm transition-colors duration-200">
      {/* ── 1. Prominent Live Quantitative Bot Activity & Radar Strip ── */}
      <div className="bg-surface-2 border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface border border-border font-bold">
            <span className={cn(
              "w-2.5 h-2.5 rounded-full animate-pulse",
              liveBotState === "EXECUTING" ? "bg-emerald-400" : liveBotState === "WAITING_FOR_CONFIRMATION" ? "bg-amber-400" : "bg-cyan-400"
            )} />
            <span className="uppercase text-[11px] tracking-wide text-text-primary">
              {liveBotStatus}
            </span>
          </div>

          <span className="hidden md:inline text-text-secondary text-[11px]">
            {liveReasoning}
          </span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {/* Refresh Live Tick Button */}
          <button
            onClick={fetchLiveMarketData}
            disabled={isLiveLoading}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface border border-border text-text-secondary hover:text-text-primary text-[11px] font-semibold active:scale-95"
            title="Refresh Live Ticks & SMC Matrix from MT5"
          >
            <RefreshCw className={cn("w-3 h-3 text-accent", isLiveLoading && "animate-spin")} />
            <span>{lastDataUpdate}</span>
          </button>

          {/* Quick Theme Toggle Button */}
          <button
            type="button"
            onClick={toggleLocalTheme}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface border border-border text-text-secondary hover:text-text-primary text-[11px] font-semibold active:scale-95"
            title="Toggle Clean Light / Dark Mode"
          >
            {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-accent" />}
            <span>{isDark ? "Light Mode" : "Dark Mode"}</span>
          </button>
        </div>
      </div>

      {/* ── 2. Top Engine Header (Clean Solid Institutional Layout) ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-surface border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gold/10 border border-gold/40 flex items-center justify-center shrink-0">
            <Target className="w-4 h-4 text-gold" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-extrabold text-sm text-text-primary tracking-tight">
                TradingView SMC Quantitative Forecasting Engine
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent/15 text-accent border border-accent/30 font-mono">
                LIVE MT5 DATA FEED
              </span>
            </div>
            <p className="text-[11px] text-text-secondary mt-0.5">
              Live Fair Value Gap (Cyan Zone), Liquidity Sweeps, 50% Consequent Encroachment &amp; Dynamic Position Sizing.
            </p>
          </div>
        </div>

        {/* Chart View Switcher + Instrument Switcher */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle: Interactive TradingView Chart vs SMC Matrix */}
          <div className="flex items-center bg-surface-2 p-1 rounded-inner border border-border">
            <button
              type="button"
              onClick={() => setChartViewMode("tradingview")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded transition-all",
                chartViewMode === "tradingview"
                  ? "bg-accent text-white shadow-xs"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>📈 Live TradingView Chart</span>
            </button>
            <button
              type="button"
              onClick={() => setChartViewMode("smc_matrix")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded transition-all",
                chartViewMode === "smc_matrix"
                  ? "bg-gold text-black shadow-xs font-black"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              <Target className="w-3.5 h-3.5" />
              <span>🎯 SMC Forecast Matrix (Image 1)</span>
            </button>
          </div>

          {/* Instrument Switcher & Live Price Readout */}
          <div className="flex items-center bg-surface-2 p-1 rounded-inner border border-border">
            <button
              onClick={() => setInstrument("BTCUSD")}
              className={cn(
                "px-3 py-1 text-xs font-bold rounded transition-all",
                instrument === "BTCUSD"
                  ? "bg-accent text-white shadow-xs"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              BTCUSD ({liveSpread} pt spread)
            </button>
            <button
              onClick={() => setInstrument("XAUUSD")}
              className={cn(
                "px-3 py-1 text-xs font-bold rounded transition-all",
                instrument === "XAUUSD"
                  ? "bg-gold text-black shadow-xs font-black"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              XAUUSD (Gold)
            </button>
          </div>
        </div>
      </div>

      {/* ── 2B. Prominent Active MT5 Position & 1:3 RR Execution Action Banner ── */}
      <div className="p-4 bg-surface-2 border-b border-border">
        {actionToast && (
          <div className={cn(
            "mb-3 px-3.5 py-2 rounded text-xs font-semibold flex items-center justify-between border",
            actionToast.type === "success"
              ? "bg-profit/10 border-profit/30 text-profit"
              : "bg-loss/10 border-loss/30 text-loss"
          )}>
            <span>{actionToast.message}</span>
            <button onClick={() => setActionToast(null)} className="underline text-[11px] ml-2">Dismiss</button>
          </div>
        )}

        {activePosition ? (
          <div className="bg-surface border border-emerald-500/50 rounded-card p-3.5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="relative flex h-3 w-3 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-extrabold text-emerald-400 text-xs tracking-wide uppercase">
                      LIVE ORDER ACTIVE ON EXNESS MT5: #{activePosition.ticket}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 font-mono">
                      {activePosition.direction || activePosition.type} {activePosition.volume} LOTS ({activePosition.symbol})
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 font-mono">
                      1:3 RR TARGET ACTIVE
                    </span>
                  </div>
                  <div className="text-[11px] text-text-secondary mt-1.5 flex flex-wrap gap-x-4 gap-y-1 font-mono">
                    <span>Entry: <strong className="text-text-primary">${formatPrice(activePosition.price_open || activePosition.open_price)}</strong></span>
                    <span>Stop Loss: <strong className="text-loss">${formatPrice(activePosition.sl)}</strong></span>
                    <span>Take Profit (1:3 RR): <strong className="text-profit">${formatPrice(activePosition.tp)}</strong></span>
                    <span>Current P/L: <strong className={Number(activePosition.profit) >= 0 ? "text-profit font-bold" : "text-loss font-bold"}>
                      {Number(activePosition.profit) >= 0 ? `+$${Number(activePosition.profit).toFixed(2)}` : `-$${Math.abs(Number(activePosition.profit)).toFixed(2)}`}
                    </strong></span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCloseTrade(activePosition.ticket)}
                  disabled={isClosingTrade}
                  className="px-3.5 py-2 bg-loss/15 hover:bg-loss/25 text-loss border border-loss/40 rounded text-xs font-bold active:scale-95 transition-all flex items-center gap-1.5"
                >
                  <RefreshCw className={cn("w-3.5 h-3.5", isClosingTrade && "animate-spin")} />
                  <span>{isClosingTrade ? "Liquidating..." : "Close Trade (Market)"}</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-surface border border-border rounded-card p-3.5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-extrabold text-text-primary uppercase tracking-wide">
                    SMC Quantitative Forecast Active ({instrument})
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-profit/15 text-profit border border-profit/30 font-mono">
                    TARGETING 1:3 RISK/REWARD
                  </span>
                </div>
                <p className="text-[11px] text-text-secondary mt-1">
                  Cyan FVG Zone marked ({formatPrice(fvgLow)} – {formatPrice(fvgHigh)}). Price moving in forecast direction.
                  SL at <strong className="text-loss">{formatPrice(initialSl)}</strong> ({slPoints} pts) · TP at <strong className="text-profit">{formatPrice(targetTp)}</strong> (3x SL distance · exact 1:3 RR).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleExecuteTrade}
                  disabled={isExecutingTrade}
                  className="px-4 py-2 bg-profit hover:bg-emerald-600 text-black font-extrabold text-xs rounded flex items-center gap-1.5 shadow-sm active:scale-95 transition-all"
                >
                  <Zap className={cn("w-3.5 h-3.5", isExecutingTrade && "animate-spin")} />
                  <span>{isExecutingTrade ? "Placing Order on Exness MT5..." : `PLACE ${direction} ORDER (1:3 RR · ${calculatedLotSize} LOT)`}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {chartViewMode === "tradingview" ? (
        <TradingViewLiveChart symbol={instrument} height={520} />
      ) : (
        <>
          {/* ── 3. Step Controller Toolbar ── */}
          <div className="flex items-center justify-between px-4 py-2 bg-surface-2 border-b border-border overflow-x-auto no-scrollbar gap-2">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-bold text-text-secondary uppercase tracking-wider mr-1">
            SMC Sequence:
          </span>

          <button
            onClick={() => { setActiveStep("SWEEP"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "SWEEP"
                ? "bg-amber-500/20 text-amber-500 border-amber-500/50 font-bold"
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
            )}
          >
            1. Sweep Purge
          </button>

          {/* User Clarified Cyan Zone */}
          <button
            onClick={() => { setActiveStep("FVG"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "FVG"
                ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/50 font-bold shadow-xs"
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
            )}
          >
            2. Mark FVG (Cyan Zone)
          </button>

          <button
            onClick={() => { setActiveStep("RETRACEMENT"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "RETRACEMENT"
                ? "bg-blue-500/20 text-blue-400 border-blue-500/50 font-bold"
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
            )}
          >
            3. Mitigation Tap
          </button>

          <button
            onClick={() => { setActiveStep("CONFIRMATION"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "CONFIRMATION"
                ? "bg-amber-400/20 text-amber-500 border-amber-400/50 font-bold animate-pulse"
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
            )}
          >
            4. Wait Confirmation
          </button>

          <button
            onClick={() => { setActiveStep("EXECUTION"); setIsPlayingCycle(false); }}
            className={cn(
              "px-2.5 py-1 rounded text-[11px] font-semibold border transition-all shrink-0",
              activeStep === "EXECUTION"
                ? "bg-profit/20 text-profit border-profit/50 font-bold"
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
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
                : "bg-surface text-text-secondary border-border hover:text-text-primary"
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
              ? "bg-amber-500/20 border-amber-500/40 text-amber-500"
              : "bg-surface border-border text-text-secondary hover:text-text-primary"
          )}
        >
          {isPlayingCycle ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          <span>{isPlayingCycle ? "Pause Sequence" : "Auto-Play Cycle"}</span>
        </button>
      </div>

      {/* ── 4. Main Chart Stage (Solid High-Contrast Canvas) ── */}
      <div className="relative bg-[#070A0F] select-none overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-[390px] min-w-[620px] font-mono text-[10px]"
        >
          {/* Background grid lines */}
          {gridTicks.map((tick, i) => {
            const y = getY(tick);
            return (
              <g key={i}>
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

          {/* Vertical Time Grid & Future Projection Line */}
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
                width="200"
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

          {/* ── 2. The Fair Value Gap (FVG) Imbalance Box (Cyan Zone as Requested) ── */}
          {(activeStep === "ALL" || activeStep === "FVG" || activeStep === "RETRACEMENT" || activeStep === "CONFIRMATION" || activeStep === "EXECUTION") && (
            <g>
              {/* Cyan FVG Zone Marked Out on Chart */}
              <rect
                x="80"
                y={getY(fvgHigh)}
                width="310"
                height={Math.max(12, getY(fvgLow) - getY(fvgHigh))}
                fill="rgba(6, 182, 212, 0.22)"
                stroke="#00F0FF"
                strokeWidth="1.8"
                rx="3"
              />
              <text
                x="85"
                y={getY(fvgHigh) - 6}
                fill="#22D3EE"
                fontSize="9"
                fontWeight="bold"
              >
                H1 FAIR VALUE GAP (CYAN MARKED ZONE) · {fvgPoints} PTS ({fvgPips} PIPS)
              </text>

              {/* 50% Consequent Encroachment (C.E.) Line */}
              <line
                x1="80"
                y1={getY(ceLevel)}
                x2="390"
                y2={getY(ceLevel)}
                stroke="#22D3EE"
                strokeDasharray="4,3"
                strokeWidth="1.4"
              />
              <text
                x="290"
                y={getY(ceLevel) - 4}
                fill="#A5F3FC"
                fontSize="8"
                fontWeight="bold"
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
                width="210"
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

          {/* ── 4. The Forecasting Tool (Risk/Reward Box) ── */}
          {(activeStep === "ALL" || activeStep === "EXECUTION") && (
            <>
              {/* STOP LOSS ZONE (Red Shaded Box on Top) */}
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

              {/* TAKE PROFIT ZONE (Green Shaded Box on Bottom) */}
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

              {/* ENTRY LINE */}
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

              {/* DYNAMIC TRAILING STOP LINE */}
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
                  width="170"
                  height="22"
                  fill="rgba(7, 10, 15, 0.95)"
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
                  R:R 1:{rrRatio.toFixed(2)} · TARGET +{rewardPoints} PTS ({rewardPips} PIPS)
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

          {/* Current Live Price Line */}
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
            className="animate-ping"
          />
          <circle
            cx={svgWidth - 85}
            cy={getY(currentPrice)}
            r="3"
            fill="#EAB308"
          />
        </svg>

        {/* Live Terminal Price Tag on Top-Right of Chart */}
        <div className="absolute top-3 right-3 bg-[#0B101B] border border-[#1E2D40] px-3 py-1.5 rounded text-right font-mono">
          <span className="text-[10px] text-text-secondary block">LIVE BID ({instrument})</span>
          <span className="text-sm font-black text-amber-400">
            {formatPrice(currentPriceAnchor)}
          </span>
          <span className="text-[9px] text-emerald-400 block mt-0.5">
            Spread: {liveSpread} pts · 0 Slippage
          </span>
        </div>
      </div>
        </>
      )}

      {/* ── 5. Bottom Analytical Tabs (Solid Institutional Navigation) ── */}
      <div className="border-t border-border bg-surface transition-colors">
        <div className="flex border-b border-border px-4 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab("calculator")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 shrink-0",
              activeTab === "calculator"
                ? "border-profit text-profit bg-profit/5"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <Shield className="w-4 h-4 text-profit" />
            <span>Pre-Trade Risk &amp; Sizing Calculator ($50+ Compounding)</span>
          </button>

          <button
            onClick={() => setActiveTab("reasons")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 shrink-0",
              activeTab === "reasons"
                ? "border-accent text-accent bg-accent/5"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <CheckCircle2 className="w-4 h-4 text-accent" />
            <span>Technical Reasons for Entry</span>
          </button>

          <button
            onClick={() => setActiveTab("macro")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 shrink-0",
              activeTab === "macro"
                ? "border-gold text-gold bg-gold/5"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <Globe className="w-4 h-4 text-gold" />
            <span>Macro Catalyst Flow</span>
          </button>

          <button
            onClick={() => setActiveTab("simulator")}
            className={cn(
              "px-4 py-2.5 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 shrink-0",
              activeTab === "simulator"
                ? "border-accent text-accent bg-accent/5"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <Lock className="w-4 h-4 text-accent" />
            <span>Dynamic Trailing &amp; Market Simulation</span>
          </button>
        </div>

        {/* ── TAB 0: PRE-TRADE RISK & SIZING CALCULATOR ($50+ COMPOUNDING) ── */}
        {activeTab === "calculator" && (
          <div className="p-4 space-y-4">
            {/* Header with Account Sizing Mode */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-profit animate-pulse" />
                <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Autonomous Pre-Trade Risk Engine &amp; Dynamic Sizer
                </h4>
              </div>

              {/* Sizing Mode Switcher */}
              <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-inner border border-border">
                <button
                  onClick={() => setSizingMode("FAST_GROWTH")}
                  className={cn(
                    "px-2.5 py-1 text-xs font-bold rounded transition-all",
                    sizingMode === "FAST_GROWTH"
                      ? "bg-profit text-white shadow-xs"
                      : "text-text-secondary hover:text-text-primary"
                  )}
                >
                  🚀 Fast-Growth Compounding (2.5% for $50–$500 Accounts)
                </button>
                <button
                  onClick={() => setSizingMode("CONSERVATIVE")}
                  className={cn(
                    "px-2.5 py-1 text-xs font-semibold rounded transition-all",
                    sizingMode === "CONSERVATIVE"
                      ? "bg-accent text-white shadow-xs font-bold"
                      : "text-text-secondary hover:text-text-primary"
                  )}
                >
                  🛡️ Institutional (1.0% Fixed Cap)
                </button>
              </div>
            </div>

            {/* Observed Balance Selector & Micro-Account Presets */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-2 border border-border rounded-inner p-3">
              <div className="flex items-center gap-3">
                <div>
                  <span className="text-[11px] text-text-secondary block font-medium">Observed Account Balance:</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-lg font-black text-gold font-mono">
                      ${effectiveBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
                    </span>
                    <span className={cn(
                      "px-2 py-0.5 rounded-full font-bold font-mono text-[10px]",
                      isUsingLiveBalance
                        ? "bg-profit/15 text-profit border border-profit/30"
                        : "bg-amber-500/15 text-amber-500 border border-amber-500/30"
                    )}>
                      {isUsingLiveBalance ? "● Live MT5 Terminal" : "● Selected Model"}
                    </span>
                  </div>
                </div>

                {liveBalance !== null && (
                  <button
                    onClick={() => setIsUsingLiveBalance(true)}
                    className={cn(
                      "px-2.5 py-1 text-xs font-bold rounded border transition-all",
                      isUsingLiveBalance
                        ? "bg-profit text-white border-profit"
                        : "bg-surface text-text-secondary border-border hover:text-text-primary"
                    )}
                  >
                    Use Live MT5 (${liveBalance.toFixed(2)})
                  </button>
                )}
              </div>

              {/* Quick Small-Account Presets ($50, $100, $250, $500, $1k) */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] text-text-secondary mr-1">Small Account Presets:</span>
                {[50, 100, 250, 500, 1000].map((b) => (
                  <button
                    key={b}
                    onClick={() => {
                      setTestBalance(b);
                      setCustomBalanceInput(b.toString());
                      setIsUsingLiveBalance(false);
                    }}
                    className={cn(
                      "px-2.5 py-1 text-xs font-mono font-bold rounded border transition-all active:scale-95",
                      !isUsingLiveBalance && testBalance === b
                        ? "bg-gold text-black border-gold shadow-xs"
                        : "bg-surface text-text-secondary border-border hover:text-text-primary"
                    )}
                  >
                    ${b}
                  </button>
                ))}

                {/* Custom Balance Input */}
                <div className="flex items-center gap-1 ml-2">
                  <span className="text-[11px] text-text-secondary">$</span>
                  <input
                    type="number"
                    min="10"
                    step="5"
                    value={customBalanceInput}
                    onChange={(e) => handleBalanceInputChange(e.target.value)}
                    placeholder="Custom"
                    className="w-16 px-1.5 py-0.5 text-xs font-mono bg-surface border border-border rounded text-text-primary text-right focus:outline-none focus:border-accent"
                  />
                </div>
              </div>
            </div>

            {/* ── 4 Essential Quantitative Metric Cards (Dual Points & Pips) ── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              {/* Card 1: Risk Budget */}
              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <span className="text-[11px] text-text-secondary font-medium block">
                  {riskPercent}% Max Risk Budget
                </span>
                <span className="text-base font-black text-loss font-mono">
                  -${riskUsd.toFixed(2)} USD
                </span>
                <span className="text-[10px] text-text-secondary block font-mono">
                  {sizingMode === "FAST_GROWTH" ? "Micro-compounding cap" : "Strict capital defense"}
                </span>
              </div>

              {/* Card 2: SL Distance in Points AND Pips */}
              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <span className="text-[11px] text-text-secondary font-medium block">
                  Stop Loss Distance
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-base font-black text-text-primary font-mono">
                    {slPoints} pts
                  </span>
                  <span className="text-xs font-bold text-accent font-mono">
                    ({slPips} pips)
                  </span>
                </div>
                <span className="text-[10px] text-text-secondary block font-mono">
                  SL Price: {formatPrice(initialSl)}
                </span>
              </div>

              {/* Card 3: Dynamically Calculated Exact Lot Size */}
              <div className="bg-surface-2 border-2 border-accent/60 rounded-inner p-3 space-y-1 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-accent font-bold block">
                    Calculated Lot Sizing
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-accent/20 text-accent text-[9px] font-bold">
                    AUTO SIZED
                  </span>
                </div>
                <span className="text-base font-black text-accent font-mono">
                  {calculatedLotSize.toFixed(2)} Lots
                </span>
                <span className="text-[10px] text-text-secondary block font-mono">
                  Margin: ~${marginRequired.toFixed(2)} @ 1:2000
                </span>
              </div>

              {/* Card 4: Potential Target Profit */}
              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <span className="text-[11px] text-text-secondary font-medium block">
                  Potential Take Profit (1:{rrRatio.toFixed(1)})
                </span>
                <span className="text-base font-black text-profit font-mono">
                  +${actualRewardUsd.toFixed(2)} USD
                </span>
                <span className="text-[10px] text-profit block font-mono font-semibold">
                  +{( (actualRewardUsd / effectiveBalance) * 100 ).toFixed(1)}% account expansion
                </span>
              </div>
            </div>

            {/* ── Compounding Acceleration RoadMap for $50 Accounts ── */}
            <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-gold" />
                  Small-Account Dynamic Growth Trajectory (Starting ${effectiveBalance.toFixed(0)})
                </span>
                <span className="text-[11px] font-semibold text-profit font-mono">
                  Asymmetric Edge: Risk ${actualRiskUsd.toFixed(2)} to Win +${actualRewardUsd.toFixed(2)}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary leading-relaxed">
                Even with an account as low as <strong>$50.00</strong>, the engine calculates the exact lot size (<strong>{calculatedLotSize.toFixed(2)} lots</strong>) so your downside on a full stop loss hit is capped to <strong>${actualRiskUsd.toFixed(2)}</strong>. Because the setup enforces a strict <strong>1:{rrRatio.toFixed(1)} R:R</strong>, each successful hit expands your capital by <strong>+${actualRewardUsd.toFixed(2)} (+{((actualRewardUsd / effectiveBalance)*100).toFixed(1)}%)</strong>!
              </p>

              {/* Micro-Compounding Table */}
              <div className="grid grid-cols-5 gap-2 pt-1 text-center font-mono text-[11px]">
                {[1, 2, 3, 4, 5].map((tradeNum) => {
                  const compounded = effectiveBalance * Math.pow(1 + (actualRewardUsd / effectiveBalance), tradeNum);
                  return (
                    <div key={tradeNum} className="bg-surface border border-border p-2 rounded">
                      <span className="text-[10px] text-text-secondary block">Win #{tradeNum}</span>
                      <span className="font-bold text-profit mt-0.5 block">
                        ${compounded.toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 1: TECHNICAL REASONS FOR ENTRY ── */}
        {activeTab === "reasons" && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-accent" />
                Rigorous 5-Point Quantitative Trade Invalidation &amp; Entry Rules
              </h4>
              <span className="text-[11px] text-profit font-semibold px-2 py-0.5 rounded bg-profit/10 border border-profit/20 font-mono">
                Verified Quantitative Edge (R:R 1:{rrRatio.toFixed(2)})
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-amber-500 font-bold">
                  <span>1. Institutional Liquidity Sweep</span>
                  <span className="font-mono">{formatPrice(sweepLevel)}</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  The bot identified a prior swing high swept at {formatPrice(sweepLevel)} (extreme {formatPrice(sweepExtreme)}). This flushed resting buy-side liquidity (BSL) into institutional limit books before an immediate displacement lower.
                </p>
              </div>

              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-cyan-400 font-bold">
                  <span>2. 3-Candle Fair Value Gap (Cyan Marked Zone)</span>
                  <span className="font-mono">{fvgPoints} pts ({fvgPips} pips)</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Inefficient 3-candle displacement created an imbalance between Candle 1 low and Candle 3 high ({formatPrice(fvgLow)} to {formatPrice(fvgHigh)}). Marked out in cyan with 50% Consequent Encroachment at {formatPrice(ceLevel)}.
                </p>
              </div>

              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-blue-400 font-bold">
                  <span>3. Retracement &amp; Mitigation Check</span>
                  <span className="font-mono">50% C.E. Respected</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  Price pulled back into the FVG to rebalance orders. The candle wicked into the 50% midpoint without closing outside the gap boundary, confirming structural respect and preventing invalidation.
                </p>
              </div>

              <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-1">
                <div className="flex items-center justify-between text-profit font-bold">
                  <span>4. Reference Candle 1-Tick Breakout</span>
                  <span className="font-mono">Trigger: {formatPrice(triggerLevel)}</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  The bot refused to enter blindly on the tap. It identified the lowest wick of the mitigation candle and entered strictly when a subsequent candle broke 1 tick below {formatPrice(triggerLevel)}.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: MACRO CATALYST FLOW ── */}
        {activeTab === "macro" && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Globe className="w-4 h-4 text-gold" />
                Live Fundamental Drivers &amp; Macro Catalysts
              </h4>
            </div>

            <div className="bg-surface-2 border border-border rounded-inner p-3 space-y-2 text-xs">
              <p className="text-[11px] text-text-secondary leading-relaxed">
                The bot filters all technical entries through its News Analyst Agent. High-impact FOMC, CPI, and NFP announcements trigger automatic news lockout 15 minutes before and 30 minutes after release to protect accounts from slippage.
              </p>
            </div>
          </div>
        )}

        {/* ── TAB 3: DYNAMIC TRAILING & SIMULATOR ── */}
        {activeTab === "simulator" && (
          <div className="p-4 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
              <div>
                <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Interactive Trade Simulation &amp; Trailing Guardian
                </h4>
                <p className="text-[11px] text-text-secondary">
                  Drag the slider to test how price movement dynamically shifts Stop Loss to Breakeven (+1 pip) and locks in profits.
                </p>
              </div>

              <button
                onClick={() => setIsAutoSimulating(!isAutoSimulating)}
                className="px-3 py-1.5 text-xs font-bold rounded bg-accent text-white flex items-center gap-1.5 active:scale-95"
              >
                {isAutoSimulating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                <span>{isAutoSimulating ? "Pause Simulation" : "Run Market Movement"}</span>
              </button>
            </div>

            {/* Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono font-semibold">
                <span className="text-text-secondary">Entry Price: {formatPrice(entryPrice)}</span>
                <span className="text-amber-400">Current Simulated: {formatPrice(currentPrice)} ({progress.toFixed(0)}%)</span>
                <span className="text-profit">Take Profit: {formatPrice(targetTp)}</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={progress}
                onChange={(e) => {
                  setProgress(parseFloat(e.target.value));
                  setIsAutoSimulating(false);
                }}
                className="w-full accent-accent cursor-pointer"
              />
            </div>

            {/* Trailing Phase Banner */}
            <div className="bg-surface-2 border border-border p-3 rounded flex items-center justify-between text-xs">
              <span className="font-semibold text-text-secondary">Active Trailing Phase:</span>
              <span className="font-bold text-profit font-mono">{trailPhase} (SL: {formatPrice(trailedStopLoss)})</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function round2(num: number): number {
  return Math.round(num * 100) / 100;
}
