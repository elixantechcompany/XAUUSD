"use client";

import Link from "next/link";
import {
  Zap,
  Shield,
  Layers,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Cpu,
  Lock,
  Compass,
  CheckCircle2,
  Globe,
  Radio,
  BarChart3,
  ChevronRight,
  Server,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#070A0F] text-[#F2F5F9] selection:bg-gold/30 selection:text-gold relative overflow-x-hidden">
      {/* ── Background Ambient Glow Effects ── */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-gradient-to-b from-blue-600/15 via-gold/10 to-transparent blur-[120px] pointer-events-none -z-10" />
      <div className="absolute top-[600px] right-0 w-[500px] h-[500px] bg-emerald-500/10 blur-[140px] pointer-events-none -z-10" />
      <div className="absolute top-[1200px] left-0 w-[500px] h-[500px] bg-blue-600/10 blur-[140px] pointer-events-none -z-10" />

      {/* ── Subtle Background Grid Lines ── */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1b253515_1px,transparent_1px),linear-gradient(to_bottom,#1b253515_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none -z-10" />

      {/* ── Navigation Header ── */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#070A0F]/80 border-b border-[#1B2535]/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/30 flex items-center justify-center shadow-[0_0_15px_rgba(212,175,55,0.2)] group-hover:border-gold/60 transition-all">
              <Zap className="w-4 h-4 text-gold fill-gold/20" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold tracking-tight text-base text-white flex items-center gap-1.5">
                ELIXAN <span className="text-gold font-bold">QUANT</span>
              </span>
              <span className="text-[10px] text-text-secondary tracking-widest font-mono uppercase -mt-1">
                AI Trading Desk
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold text-text-secondary">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#copier" className="hover:text-white transition-colors">Multi-Account Copier</a>
            <a href="#strategy" className="hover:text-white transition-colors">SMC Strategy</a>
            <a href="#agents" className="hover:text-white transition-colors">6-Agent Consensus</a>
            <Link href="/signals" className="hover:text-gold transition-colors flex items-center gap-1">
              <Radio className="w-3.5 h-3.5 text-gold animate-pulse" />
              Live Signals
            </Link>
          </nav>

          {/* Action CTAs */}
          <div className="flex items-center gap-3">
            <Link
              href="/auth/login"
              className="text-xs font-semibold text-text-secondary hover:text-white px-3.5 py-2 transition-colors min-h-[38px] flex items-center"
            >
              Sign In
            </Link>
            <Link
              href="/overview"
              className="flex items-center gap-1.5 px-4 py-2 rounded-inner bg-gradient-to-r from-gold via-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-bold text-xs shadow-[0_0_20px_rgba(212,175,55,0.3)] transition-all active:scale-95 min-h-[38px]"
            >
              Launch Desk
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="pt-16 sm:pt-24 pb-16 px-4 sm:px-6 max-w-7xl mx-auto text-center relative">
        {/* Floating Pill Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface border border-gold/30 text-xs font-semibold text-text-primary shadow-[0_0_25px_rgba(212,175,55,0.15)] mb-6 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
          <span>AUTONOMOUS QUANTITATIVE DESK</span>
          <span className="text-text-secondary">·</span>
          <span className="text-gold font-mono text-[11px]">EXNESS MT5 IPC BRIDGE</span>
        </div>

        {/* Hero Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.1] sm:leading-[1.15]">
          Institutional AI Trading for{" "}
          <span className="bg-gradient-to-r from-gold via-amber-300 to-yellow-500 bg-clip-text text-transparent">
            Gold & Bitcoin.
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="mt-6 text-sm sm:text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
          Autonomous Fair Value Gap (FVG) and Liquidity Sweep execution. Runs in-process on your laptop with single-terminal multi-account trade copying in &lt;200ms.
        </p>

        {/* CTA Buttons */}
        <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/overview"
            className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-8 py-3.5 rounded-inner bg-gradient-to-r from-gold via-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-extrabold text-sm shadow-[0_0_30px_rgba(212,175,55,0.35)] transition-all active:scale-95 min-h-[48px]"
          >
            Launch Live Trading Desk
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/signals"
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 rounded-inner bg-[#121821]/80 hover:bg-[#1A2230] text-text-primary font-semibold text-sm border border-[#243043] transition-all min-h-[48px]"
          >
            <Compass className="w-4 h-4 text-accent" />
            Explore Live Signals & Measuring Tool
          </Link>
        </div>

        {/* Trust Badges */}
        <div className="mt-14 pt-8 border-t border-[#1B2535]/60 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
          <div className="bg-[#121821]/50 border border-[#243043]/60 rounded-card p-3.5">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Architecture</span>
            <p className="text-sm font-bold text-white mt-1">Single MT5 Process</p>
            <span className="text-[11px] text-emerald-400 mt-0.5 block">&lt; 85 MB RAM Overhead</span>
          </div>

          <div className="bg-[#121821]/50 border border-[#243043]/60 rounded-card p-3.5">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Execution Latency</span>
            <p className="text-sm font-bold text-white mt-1">&lt; 200ms Copier Sync</p>
            <span className="text-[11px] text-accent mt-0.5 block">Fast-Switch IPC Bridge</span>
          </div>

          <div className="bg-[#121821]/50 border border-[#243043]/60 rounded-card p-3.5">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Risk Control</span>
            <p className="text-sm font-bold text-white mt-1">1:2.0 Minimum R:R</p>
            <span className="text-[11px] text-gold mt-0.5 block">Strict 1.0% Equity Risk</span>
          </div>

          <div className="bg-[#121821]/50 border border-[#243043]/60 rounded-card p-3.5">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Security</span>
            <p className="text-sm font-bold text-white mt-1">Zero Cloud Passwords</p>
            <span className="text-[11px] text-text-secondary mt-0.5 block">Windows Credential Mgr</span>
          </div>
        </div>
      </section>

      {/* ── Live Market Status Ticker ── */}
      <section className="py-4 border-y border-[#1B2535] bg-[#0D131C]/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-bold text-white tracking-wide uppercase">Markets Monitored:</span>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="font-bold text-gold">XAUUSD (Gold):</span>
              <span className="text-text-secondary font-mono">H1 Structural FVG · London / NY Golden Overlap</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-accent">BTCUSD (Bitcoin):</span>
              <span className="text-text-secondary font-mono">24/7 Continuous Liquidity · Volatility Active</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-text-secondary">
            <Globe className="w-3.5 h-3.5 text-accent" />
            <span>Exness Standard & Pro Symbols Auto-Resolved</span>
          </div>
        </div>
      </section>

      {/* ── Three Core Engineering Pillars ── */}
      <section id="features" className="py-20 px-4 sm:px-6 max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-xs font-bold text-gold uppercase tracking-widest">Built For Professional Traders</h2>
          <p className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
            Engineered For Speed, Precision, & Capital Preservation
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Pillar 1 */}
          <div className="bg-gradient-to-b from-[#121821] to-[#0D131C] border border-[#243043] rounded-card p-6 relative overflow-hidden group hover:border-gold/40 transition-all">
            <div className="w-12 h-12 rounded-inner bg-gold/10 border border-gold/20 flex items-center justify-center mb-5 text-gold shadow-[0_0_20px_rgba(212,175,55,0.15)]">
              <Server className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Single-Terminal Multi-Account Copier</h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              Leave only 1 MT5 window open on your laptop. The engine trades the master and replicates deals across all child accounts in &lt;200ms with individual 1.0% risk sizing without crashing your machine.
            </p>
            <ul className="space-y-2 text-xs text-text-secondary border-t border-[#1B2535] pt-4 font-medium">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Zero multi-terminal memory bloat (&lt; 85 MB RAM)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Proportional lot sizing tailored to each child balance
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Global Kill Switch liquidates all accounts in 1 click
              </li>
            </ul>
          </div>

          {/* Pillar 2 */}
          <div className="bg-gradient-to-b from-[#121821] to-[#0D131C] border border-[#243043] rounded-card p-6 relative overflow-hidden group hover:border-accent/40 transition-all">
            <div className="w-12 h-12 rounded-inner bg-accent/10 border border-accent/20 flex items-center justify-center mb-5 text-accent shadow-[0_0_20px_rgba(59,130,246,0.15)]">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">6-Agent Autonomous Deliberations</h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              Six specialized AI agents deliberate in &lt;20ms before any deal is placed: The Scout, The News Analyst, The Chart Analyst, The Skeptic, The Risk Manager, and The Execution Manager.
            </p>
            <ul className="space-y-2 text-xs text-text-secondary border-t border-[#1B2535] pt-4 font-medium">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Dual Veto Powers: Skeptic & Risk Manager can abort
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                High-impact economic news filter lockouts
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Strict maximum 3 consecutive loss circuit breaker
              </li>
            </ul>
          </div>

          {/* Pillar 3 */}
          <div className="bg-gradient-to-b from-[#121821] to-[#0D131C] border border-[#243043] rounded-card p-6 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
            <div className="w-12 h-12 rounded-inner bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.15)]">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Profit Guardian & Retracement Shield</h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              Protects every dollar made. Automatically shifts Stop Loss to Breakeven (+1 pip) at 1.0R, trails behind structure, and locks in banked gains if market experiences an aggressive pullback.
            </p>
            <ul className="space-y-2 text-xs text-text-secondary border-t border-[#1B2535] pt-4 font-medium">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Breakeven shift at 1.0R (100% risk-free trade)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Locks +0.5R at 1.5R, +1.0R at 2.0R
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Aggressive Retracement Guardian: locks 50% profit
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── Interactive Setup Architecture (Part 3 SMC Strategy) ── */}
      <section id="strategy" className="py-16 px-4 sm:px-6 max-w-7xl mx-auto border-t border-[#1B2535]">
        <div className="bg-gradient-to-br from-[#121821] via-[#0D131C] to-[#070A0F] border border-[#243043] rounded-card p-8 sm:p-12 relative overflow-hidden">
          <div className="max-w-2xl">
            <span className="text-xs font-bold text-gold uppercase tracking-wider block">Deterministic Execution Protocol</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mt-2">
              The 5-Step Smart Money Sequence
            </h2>
            <p className="text-xs text-text-secondary mt-2 leading-relaxed">
              Every trade strictly adheres to the 5-step sequence with zero subjective guesswork:
            </p>

            <div className="mt-8 space-y-4">
              <div className="flex items-start gap-3.5">
                <span className="w-6 h-6 rounded-full bg-gold/15 text-gold border border-gold/30 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">1</span>
                <div>
                  <h4 className="text-sm font-bold text-white">Liquidity Sweep</h4>
                  <p className="text-xs text-text-secondary mt-0.5">Asian or prior session swing high/low swept with an extreme rejection wick.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <span className="w-6 h-6 rounded-full bg-gold/15 text-gold border border-gold/30 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">2</span>
                <div>
                  <h4 className="text-sm font-bold text-white">3-Candle Fair Value Gap (FVG)</h4>
                  <p className="text-xs text-text-secondary mt-0.5">Forms an unmistakable price imbalance meeting minimum ATR and tick thresholds.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <span className="w-6 h-6 rounded-full bg-gold/15 text-gold border border-gold/30 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">3</span>
                <div>
                  <h4 className="text-sm font-bold text-white">Retracement Into Gap</h4>
                  <p className="text-xs text-text-secondary mt-0.5">Price pulls back into the FVG zone, tapping institutional orders.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <span className="w-6 h-6 rounded-full bg-gold/15 text-gold border border-gold/30 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">4</span>
                <div>
                  <h4 className="text-sm font-bold text-white">Reference Candle Freeze</h4>
                  <p className="text-xs text-text-secondary mt-0.5">The exact candle that entered the gap is permanently frozen as the reference level.</p>
                </div>
              </div>

              <div className="flex items-start gap-3.5">
                <span className="w-6 h-6 rounded-full bg-gold/15 text-gold border border-gold/30 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">5</span>
                <div>
                  <h4 className="text-sm font-bold text-white">Tick Breakout Dispatch (&lt;50ms)</h4>
                  <p className="text-xs text-text-secondary mt-0.5">Market breaches reference candle extreme; order dispatched instantly with attached SL and 1:2.0 TP.</p>
                </div>
              </div>
            </div>

            <div className="mt-8 flex gap-3">
              <Link
                href="/signals"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-inner bg-accent hover:bg-blue-600 text-white font-bold text-xs transition-all"
              >
                Inspect Live Setups
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Ready to Trade Bottom Banner ── */}
      <section className="py-20 px-4 sm:px-6 text-center max-w-4xl mx-auto">
        <div className="bg-gradient-to-b from-[#121821] to-[#0A0E15] border border-gold/30 rounded-card p-10 relative overflow-hidden shadow-[0_0_50px_rgba(212,175,55,0.1)]">
          <h2 className="text-3xl font-extrabold text-white">
            Ready to Run Your AI Trading Desk?
          </h2>
          <p className="text-sm text-text-secondary max-w-xl mx-auto mt-3">
            Open MetaTrader 5 on your laptop, connect your Exness accounts, and trade with institutional discipline and automated risk management.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/overview"
              className="w-full sm:w-auto px-8 py-3.5 rounded-inner bg-gradient-to-r from-gold via-amber-500 to-yellow-500 text-black font-extrabold text-sm shadow-[0_0_25px_rgba(212,175,55,0.3)] transition-all active:scale-95 min-h-[46px] flex items-center justify-center gap-2"
            >
              Open Trading Desk
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/auth/signup"
              className="w-full sm:w-auto px-6 py-3.5 rounded-inner bg-[#1A2230] text-white font-semibold text-sm border border-[#243043] hover:border-gold/40 transition-all min-h-[46px] flex items-center justify-center"
            >
              Create Account
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[#1B2535] bg-[#05070A] py-10 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text-secondary">
          <div className="flex items-center gap-2.5">
            <Zap className="w-4 h-4 text-gold" />
            <span className="font-bold text-white">ELIXAN QUANT AI DESK</span>
            <span>·</span>
            <span>Exness MetaTrader 5 IPC Bridge</span>
          </div>
          <p className="text-[11px]">
            Risk Warning: Trading leveraged instruments carries risk. Passwords stored only on local machine.
          </p>
        </div>
      </footer>
    </div>
  );
}
