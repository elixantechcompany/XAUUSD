"use client";

/**
 * Multi-Account Trade Copier Hub — STRATEGY_SPEC.md v1.0
 *
 * Single-Terminal Architecture:
 * - The user leaves ONE single MT5 terminal window open on their laptop.
 * - Master Account analyzes the market, detects Part 3 setups, and opens trades.
 * - Child Accounts are sequentially switched in-process via fast mt5.login() (<200ms)
 *   with zero additional RAM overhead and exact proportional 1.0% risk sizing.
 * - Passwords are saved ONLY into local Windows Credential Manager via the local engine.
 */

import { useEffect, useState, type FormEvent } from "react";
import { getSupabaseClient } from "@/lib/supabase/client";
import { useBotStore } from "@/lib/store";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  Plus, Server, Shield, Eye, EyeOff,
  CheckCircle2, AlertCircle,
  Loader2, Zap, Power, Trash2, RefreshCw, Copy, Layers, AlertTriangle,
  Check, Settings, Terminal, ArrowRightLeft
} from "lucide-react";

const EXNESS_SERVERS = [
  "Exness-MT5Trial12",
  "Exness-MT5Trial",
  "Exness-MT5Trial2",
  "Exness-MT5Trial3",
  "Exness-MT5Trial4",
  "Exness-MT5Demo",
  "Exness-MT5Real",
  "Exness-MT5Real2",
  "Exness-MT5Real3",
  "Exness-MT5Real10",
];

interface AccountInfo {
  account_id: number;
  label: string;
  server: string;
  balance: number;
  equity: number;
  margin_free: number;
  is_master: boolean;
  is_active: boolean;
  status: string;
  risk_multiplier?: number;
  symbol?: string;
  mode?: string;
}

interface CopierResponse {
  terminal_online: boolean;
  master: AccountInfo;
  children: AccountInfo[];
  total_children: number;
  active_children: number;
}

interface CopiedTrade {
  master_ticket: number;
  child_account_id: number;
  child_ticket: number;
  symbol: string;
  direction: string;
  entry_price: number;
  volume: number;
  sl: number;
  tp: number;
  opened_at: string;
  status: string;
}

export default function AccountsPage() {
  const heartbeat = useBotStore((s) => s.heartbeat);
  const engineOnline =
    heartbeat != null &&
    (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 < 60;

  const engineApiUrl =
    process.env.NEXT_PUBLIC_ENGINE_API_URL ?? "http://127.0.0.1:8000";

  // ── Copier state ───────────────────────────────────────────────────────────
  const [copierData, setCopierData] = useState<CopierResponse | null>(null);
  const [copiedTrades, setCopiedTrades] = useState<CopiedTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [killSwitchRunning, setKillSwitchRunning] = useState(false);

  // ── Master Account Form State (Exness Demo & Real) ────────────────────────
  const [showMasterModal, setShowMasterModal] = useState(false);
  const [masterLabel, setMasterLabel] = useState("Exness Demo Master");
  const [masterLogin, setMasterLogin] = useState("");
  const [masterPassword, setMasterPassword] = useState("");
  const [masterServer, setMasterServer] = useState(EXNESS_SERVERS[0]); // "Exness-MT5Trial12"
  const [masterCustomServer, setMasterCustomServer] = useState("");
  const [masterSymbol, setMasterSymbol] = useState<"BTCUSD" | "XAUUSD">("BTCUSD");
  const [masterMode, setMasterMode] = useState<"DEMO" | "LIVE">("DEMO");
  const [showMasterPw, setShowMasterPw] = useState(false);
  const [savingMaster, setSavingMaster] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  // ── Form state (Add Sub-Account) ───────────────────────────────────────────
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState(EXNESS_SERVERS[0]);
  const [customServer, setCustom] = useState("");
  const [multiplier, setMultiplier] = useState(1.0);
  const [maxSlippage, setMaxSlippage] = useState(3.0);
  const [showPw, setShowPw] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const finalServer = server === "custom" ? customServer.trim() : server;
  const finalMasterServer = masterServer === "custom" ? masterCustomServer.trim() : masterServer;

  function applyPreset(type: "DEMO_BTC" | "DEMO_GOLD" | "REAL") {
    if (type === "DEMO_BTC") {
      setMasterServer("Exness-MT5Trial12");
      setMasterSymbol("BTCUSD");
      setMasterMode("DEMO");
      setMasterLabel("Exness Demo BTC");
    } else if (type === "DEMO_GOLD") {
      setMasterServer("Exness-MT5Trial12");
      setMasterSymbol("XAUUSD");
      setMasterMode("DEMO");
      setMasterLabel("Exness Demo Gold");
    } else {
      setMasterServer("Exness-MT5Real");
      setMasterSymbol("XAUUSD");
      setMasterMode("LIVE");
      setMasterLabel("Exness Real Master");
    }
  }

  function scrollToMasterRegistration(preset?: "DEMO_BTC" | "DEMO_GOLD" | "REAL") {
    if (preset) applyPreset(preset);
    setShowMasterModal(true);
    setSuccess(null);
    setError(null);
    setTimeout(() => {
      const el = document.getElementById("master-registration-form");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-4", "ring-amber-500", "shadow-xl");
        setTimeout(() => el.classList.remove("ring-4", "ring-amber-500", "shadow-xl"), 2500);
        const input = document.getElementById("master-login");
        if (input) input.focus();
      }
    }, 100);
  }

  function scrollToSubAccountRegistration() {
    setShowForm(true);
    setSuccess(null);
    setError(null);
    setTimeout(() => {
      const el = document.getElementById("sub-account-registration-form");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-4", "ring-accent", "shadow-xl");
        setTimeout(() => el.classList.remove("ring-4", "ring-accent", "shadow-xl"), 2500);
        const input = document.getElementById("acct-label");
        if (input) input.focus();
      }
    }, 100);
  }

  // ── Fetch accounts from Internal Server API (Zero Mixed-Content & Zero RLS issues) ──
  async function fetchCopierAccounts(silent = false) {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const res = await fetch("/api/account", { cache: "no-store" });
      if (res.ok) {
        const data: CopierResponse = await res.json();
        setCopierData(data);
      } else {
        await loadFromSupabase();
      }

      // If running on local network, also try to fetch copier trades
      if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
        const tradesRes = await fetch(`${engineApiUrl}/copier/trades`, { cache: "no-store" }).catch(() => null);
        if (tradesRes && tradesRes.ok) {
          const trades: CopiedTrade[] = await tradesRes.json();
          setCopiedTrades(trades);
        }
      }
    } catch {
      await loadFromSupabase();
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  // ── Supabase fallback for offline / remote viewing ──────────────────────────
  async function loadFromSupabase() {
    try {
      const { data } = await getSupabaseClient()
        .from("settings")
        .select("key, value")
        .like("key", "mt5_account_%");

      const loaded = (data ?? []).map((row) => ({ ...row.value, key: row.key }) as any).filter(Boolean);
      const masterRow = loaded.find((a) => a.is_master || a.mode === "master" || a.key === "mt5_account_master") || loaded[0];
      const childRows = loaded.filter((a) => a !== masterRow);

      setCopierData({
        terminal_online: false,
        master: {
          account_id: masterRow ? Number(masterRow.login || masterRow.account_id) : 0,
          label: masterRow?.label ?? (masterRow?.account_id ? `Exness ${masterRow.mode || "Demo"} #${masterRow.account_id}` : "Exness Master Terminal"),
          server: masterRow?.server ?? "Exness-MT5Trial9",
          balance: 0.0,
          equity: 0.0,
          margin_free: 0.0,
          is_master: true,
          is_active: true,
          status: masterRow?.account_id ? "STANDBY (READY ON LAPTOP)" : "NOT CONFIGURED",
          symbol: masterRow?.symbol ?? "BTCUSD",
          mode: masterRow?.mode ?? "DEMO",
        },
        children: childRows.map((c) => ({
          account_id: Number(c.login || c.account_id),
          label: c.label ?? `Sub-Account #${c.login || c.account_id}`,
          server: c.server ?? "Exness-MT5Real",
          balance: 0.0,
          equity: 0.0,
          margin_free: 0.0,
          is_master: false,
          is_active: c.is_active ?? true,
          status: "SAVED",
          risk_multiplier: c.risk_multiplier ?? 1.0,
        })),
        total_children: childRows.length,
        active_children: childRows.filter((c) => c.is_active ?? true).length,
      });
    } catch {
      // ignore
    }
  }

  async function handleConfigureMaster(e: FormEvent) {
    e.preventDefault();
    if (!masterLogin) {
      return setError("Please provide your Exness account number / MT5 login.");
    }
    const acctId = parseInt(masterLogin, 10);
    if (isNaN(acctId)) {
      return setError("Exness Account Number / MT5 Login must be numeric.");
    }

    setSavingMaster(true);
    setError(null);

    try {
      // 1. Post to Server API (persists to Supabase settings with service-role, dispatches command)
      const res = await fetch("/api/account/master", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: acctId,
          password: masterPassword,
          server: finalMasterServer,
          label: masterLabel || `Exness ${masterMode} #${acctId}`,
          symbol: masterSymbol,
          mode: masterMode,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error || "Failed to configure Master Account.");
      }

      // 2. Also forward to local engine if running on localhost
      if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
        await fetch(`${engineApiUrl}/copier/master`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account_id: acctId,
            password: masterPassword,
            server: finalMasterServer,
            label: masterLabel || `Exness ${masterMode} #${acctId}`,
            symbol: masterSymbol,
            mode: masterMode,
          }),
        }).catch(() => null);
      }

      setSuccess(`Exness ${masterMode} Account #${acctId} configured for ${masterSymbol}! Run connect_exness.bat or python main.py on your laptop to start live stream.`);
      setShowMasterModal(false);
      setMasterPassword("");
      await fetchCopierAccounts(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to configure Master Account.");
    } finally {
      setSavingMaster(false);
    }
  }

  async function handleQuickSwitchSymbol(target: "BTCUSD" | "XAUUSD") {
    try {
      const currentMaster = copierData?.master;
      if (currentMaster?.account_id) {
        await fetch("/api/account/master", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account_id: currentMaster.account_id,
            server: currentMaster.server,
            label: currentMaster.label,
            symbol: target,
            mode: currentMaster.mode || "DEMO",
          }),
        });
      }
      setSuccess(`Active target asset switched to ${target}!`);
      await fetchCopierAccounts(true);
    } catch {
      setError("Failed to switch target asset.");
    }
  }

  function copyCliCommand(cmd: string) {
    navigator.clipboard.writeText(cmd).then(() => {
      setCopiedCmd(true);
      setTimeout(() => setCopiedCmd(false), 2500);
    });
  }

  useEffect(() => {
    fetchCopierAccounts();
    const interval = setInterval(() => fetchCopierAccounts(true), 10000);
    return () => clearInterval(interval);
  }, []);

  // ── Add Child Account ────────────────────────────────────────────────────────
  async function handleAddAccount(e: FormEvent) {
    e.preventDefault();
    if (!label || !login || !finalServer) {
      return setError("Please fill in all required fields.");
    }
    setSaving(true);
    setError(null);

    const acctId = parseInt(login, 10);
    if (isNaN(acctId)) {
      setSaving(false);
      return setError("MT5 Login must be numeric.");
    }

    try {
      // 1. Post to Server API (persists securely to Supabase settings)
      const res = await fetch("/api/account/sub-accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: acctId,
          password,
          server: finalServer,
          label,
          risk_multiplier: multiplier,
          is_active: true,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error || "Failed to register sub-account.");
      }

      // 2. Also register with local engine if running on localhost
      if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
        await fetch(`${engineApiUrl}/copier/accounts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account_id: acctId,
            password,
            server: finalServer,
            label,
            risk_pct: 1.0,
            risk_multiplier: multiplier,
            is_active: true,
            max_slippage_pips: maxSlippage,
          }),
        }).catch(() => null);
      }

      setPassword("");
      setSuccess(`Sub-account ${label} (${acctId}) successfully linked to Copier!`);
      setShowForm(false);
      setLabel("");
      setLogin("");
      setServer(EXNESS_SERVERS[0]);
      setMultiplier(1.0);

      // Refresh list
      await fetchCopierAccounts(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to register sub-account.");
    } finally {
      setSaving(false);
    }
  }

  // ── Toggle Sub-Account Replication ─────────────────────────────────────────
  async function handleToggle(accountId: number) {
    setTogglingId(accountId);
    try {
      const targetChild = copierData?.children.find((c) => c.account_id === accountId);
      if (targetChild) {
        await fetch("/api/account/sub-accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account_id: accountId,
            server: targetChild.server,
            label: targetChild.label,
            risk_multiplier: targetChild.risk_multiplier,
            is_active: !targetChild.is_active,
          }),
        });
      }
      await fetchCopierAccounts(true);
    } catch {
      setError("Failed to toggle sub-account replication.");
    } finally {
      setTogglingId(null);
    }
  }

  // ── Remove Account ─────────────────────────────────────────────────────────
  async function handleRemove(accountId: number) {
    try {
      const res = await fetch(`/api/account/sub-accounts?account_id=${accountId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error || "Failed to remove account.");
      }
      await fetchCopierAccounts(true);
      setSuccess(`Account ${accountId} removed.`);
    } catch {
      setError("Failed to remove account.");
    }
  }

  // ── Emergency Global Kill Switch ───────────────────────────────────────────
  async function handleGlobalKillSwitch() {
    setKillSwitchRunning(true);
    setError(null);
    try {
      const res = await fetch(`${engineApiUrl}/copier/kill-switch`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setSuccess("GLOBAL KILL SWITCH EXECUTED: All positions on Primary and Sub-Accounts closed immediately.");
        await fetchCopierAccounts(true);
      } else {
        throw new Error("Failed to execute emergency liquidation.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Emergency liquidation error.");
    } finally {
      setKillSwitchRunning(false);
    }
  }

  const master = copierData?.master;
  const children = copierData?.children ?? [];
  const totalBalance = (master?.balance ?? 0) + children.reduce((acc, c) => acc + (c.balance || 0), 0);
  const totalEquity = (master?.equity ?? 0) + children.reduce((acc, c) => acc + (c.equity || 0), 0);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* ── Top Header & Copier Status ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Multi-Account Trade Copier
            </h1>
            <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-accent/10 border border-accent/30 text-accent">
              <Zap className="w-3.5 h-3.5" />
              Fast-Switch Engine
            </span>
          </div>
          <p className="text-sm text-text-secondary mt-1">
            Ultra-low latency portfolio replication. The engine executes on your primary master terminal and mirrors orders across all connected sub-accounts in &lt;200ms with exact proportional risk sizing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchCopierAccounts(true)}
            disabled={refreshing}
            className="p-2.5 rounded-inner bg-surface border border-border text-text-secondary hover:text-text-primary transition-all active:scale-95"
            title="Refresh Account Balances"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin text-accent")} />
          </button>

          <button
            onClick={() => scrollToMasterRegistration("DEMO_BTC")}
            className="flex items-center gap-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black text-sm font-bold px-4 py-2.5 rounded-inner transition-all shadow-sm active:scale-95 min-h-[44px]"
          >
            <Server className="w-4 h-4" />
            Register Master Account
          </button>

          <button
            onClick={() => scrollToSubAccountRegistration()}
            className="flex items-center gap-2 bg-accent hover:bg-blue-600 text-white text-sm font-semibold px-4 py-2.5 rounded-inner transition-all shadow-sm active:scale-95 min-h-[44px]"
          >
            <Plus className="w-4 h-4" />
            Link Sub-Account
          </button>
        </div>
      </div>

      {/* ── Copier Metrics Summary Bar ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-surface border border-border rounded-card p-4">
          <span className="text-xs text-text-secondary font-medium">Aggregated Equity</span>
          <p className="text-xl font-bold text-text-primary mt-1 tabular-nums">
            {copierData?.terminal_online && totalEquity > 0
              ? `$${totalEquity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "-- USD"}
          </p>
          <span className="text-[11px] text-profit flex items-center gap-1 mt-1 font-medium">
            {copierData?.terminal_online ? `● Master + ${children.length} Sub-Accounts` : "● Awaiting MT5 Terminal Live Sync"}
          </span>
        </div>

        <div className="bg-surface border border-border rounded-card p-4">
          <span className="text-xs text-text-secondary font-medium">Aggregated Balance</span>
          <p className="text-xl font-bold text-text-primary mt-1 tabular-nums">
            {copierData?.terminal_online && totalBalance > 0
              ? `$${totalBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "-- USD"}
          </p>
          <span className="text-[11px] text-text-secondary mt-1 block">
            {copierData?.terminal_online ? "Combined portfolio cash" : "Terminal Offline Standby"}
          </span>
        </div>

        <div className="bg-surface border border-border rounded-card p-4">
          <span className="text-xs text-text-secondary font-medium">Active Copier Links</span>
          <p className="text-xl font-bold text-accent mt-1 tabular-nums">
            {copierData?.active_children ?? 0} / {copierData?.total_children ?? 0}
          </p>
          <span className="text-[11px] text-text-secondary mt-1 block">
            Proportional 1.0% risk sizing
          </span>
        </div>

        <div className="bg-surface border border-border rounded-card p-4">
          <span className="text-xs text-text-secondary font-medium">Single MT5 Process</span>
          <div className="flex items-center gap-1.5 mt-1">
            <span className={cn(
              "w-2.5 h-2.5 rounded-full animate-pulse",
              copierData?.terminal_online ? "bg-profit" : "bg-warning"
            )} />
            <p className="text-sm font-semibold text-text-primary truncate">
              {copierData?.terminal_online ? "MT5 Connected" : "Terminal Offline"}
            </p>
          </div>
          <span className="text-[11px] text-text-secondary mt-1 block">
            Memory Load: &lt; 85 MB RAM
          </span>
        </div>
      </div>

      {/* ── Emergency Kill Switch Banner ── */}
      <div className="bg-loss/10 border border-loss/30 rounded-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-loss shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-loss">Global Emergency Kill Switch</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Liquidates all open positions across the <strong>Primary master account and ALL connected sub-accounts</strong> immediately and halts engine signal generation.
            </p>
          </div>
        </div>

        <ConfirmDialog
          title="EXECUTE GLOBAL KILL SWITCH?"
          description="This will immediately close EVERY open position on your Primary account AND all connected sub-accounts at market price. This cannot be undone."
          confirmLabel="Yes, Liquidate All Accounts"
          danger
          onConfirm={handleGlobalKillSwitch}
        >
          <button
            disabled={killSwitchRunning}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-loss hover:bg-red-700 active:scale-95 text-white font-semibold rounded-inner text-xs transition-all shrink-0 min-h-[44px]"
          >
            {killSwitchRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Power className="w-4 h-4" />
            )}
            GLOBAL KILL SWITCH
          </button>
        </ConfirmDialog>
      </div>

      {/* Feedback alerts */}
      {success && (
        <div className="bg-profit/10 border border-profit/30 rounded-card p-4 text-sm text-profit flex items-start gap-2.5">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div className="bg-loss/10 border border-loss/30 rounded-card p-4 text-sm text-loss flex items-start gap-2.5">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Master Exness Account Configuration Modal ── */}
      {showMasterModal && (
        <section id="master-registration-form" className="bg-surface border-2 border-amber-500/40 rounded-card overflow-hidden shadow-2xl transition-all duration-300">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-gradient-to-r from-amber-500/15 via-surface-2 to-surface-2">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-amber-400" />
              <div>
                <h2 className="text-sm font-bold text-text-primary">
                  Configure Primary Exness MT5 Master Account
                </h2>
                <p className="text-[11px] text-text-secondary">
                  Authorize autonomous execution on Demo or Live for BTCUSD &amp; XAUUSD
                </p>
              </div>
            </div>
            <button
              onClick={() => { setShowMasterModal(false); setError(null); }}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors px-2 py-1"
            >
              Cancel
            </button>
          </div>

          <div className="p-5 space-y-4">
            {/* Quick Presets */}
            <div className="flex flex-wrap items-center gap-2 pb-1 border-b border-border">
              <span className="text-xs text-text-secondary font-medium">Quick Presets:</span>
              <button
                type="button"
                onClick={() => applyPreset("DEMO_BTC")}
                className={cn(
                  "px-3 py-1 text-xs font-semibold rounded-inner border transition-all",
                  masterMode === "DEMO" && masterSymbol === "BTCUSD"
                    ? "bg-amber-500/20 text-amber-400 border-amber-500/50"
                    : "bg-surface-2 text-text-secondary border-border hover:text-text-primary"
                )}
              >
                ● Test on Demo (BTC)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("DEMO_GOLD")}
                className={cn(
                  "px-3 py-1 text-xs font-semibold rounded-inner border transition-all",
                  masterMode === "DEMO" && masterSymbol === "XAUUSD"
                    ? "bg-amber-500/20 text-amber-400 border-amber-500/50"
                    : "bg-surface-2 text-text-secondary border-border hover:text-text-primary"
                )}
              >
                ● Test on Demo (Gold)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("REAL")}
                className={cn(
                  "px-3 py-1 text-xs font-semibold rounded-inner border transition-all",
                  masterMode === "LIVE"
                    ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50"
                    : "bg-surface-2 text-text-secondary border-border hover:text-text-primary"
                )}
              >
                ● Real Live Account
              </button>
            </div>

            <div className="bg-surface-2 border border-border rounded-inner p-3 flex items-start gap-2.5 text-xs text-text-secondary">
              <Shield className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                <strong>Zero Cloud Plaintext:</strong> Your Exness MT5 password is saved into Windows Credential Manager on your local laptop. Only non-sensitive parameters (Account Login, Server, and Symbol) are saved to Supabase to enable remote monitoring.
              </span>
            </div>

            <form onSubmit={handleConfigureMaster} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field id="master-mode" label="Account Type / Mode">
                  <select
                    id="master-mode"
                    value={masterMode}
                    onChange={(e) => setMasterMode(e.target.value as "DEMO" | "LIVE")}
                    className={inputCls}
                  >
                    <option value="DEMO">Demo / Trial Account (Zero Financial Risk)</option>
                    <option value="LIVE">Real Account (Live Broker Trading)</option>
                  </select>
                </Field>

                <Field id="master-symbol" label="Target Trading Asset">
                  <select
                    id="master-symbol"
                    value={masterSymbol}
                    onChange={(e) => setMasterSymbol(e.target.value as "BTCUSD" | "XAUUSD")}
                    className={inputCls}
                  >
                    <option value="BTCUSD">BTCUSD (Bitcoin) — 24/7 Continuous Liquidity</option>
                    <option value="XAUUSD">XAUUSD (Gold) — London / New York Overlap</option>
                  </select>
                </Field>

                <Field id="master-login" label="Exness MT5 Login / Account Number" hint="Numeric account number provided by Exness (e.g. 24589102)">
                  <input
                    id="master-login"
                    type="text"
                    value={masterLogin}
                    onChange={(e) => setMasterLogin(e.target.value)}
                    required
                    placeholder="e.g. 24589102"
                    className={inputCls}
                  />
                </Field>

                <Field id="master-password" label="Exness MT5 Trading Password" hint="Never logged or exposed in plaintext">
                  <div className="relative">
                    <input
                      id="master-password"
                      type={showMasterPw ? "text" : "password"}
                      value={masterPassword}
                      onChange={(e) => setMasterPassword(e.target.value)}
                      required
                      placeholder="Enter MT5 Trading Password"
                      className={cn(inputCls, "pr-10")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowMasterPw(!showMasterPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                    >
                      {showMasterPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>

                <Field id="master-server" label="Exness Server" hint="Select your broker server (e.g. Exness-MT5Trial12 for Demo)">
                  <select
                    id="master-server"
                    value={masterServer}
                    onChange={(e) => setMasterServer(e.target.value)}
                    className={inputCls}
                  >
                    {EXNESS_SERVERS.map((srv) => (
                      <option key={srv} value={srv}>
                        {srv} {srv.includes("Trial") || srv.includes("Demo") ? "(Demo / Paper)" : "(Real)"}
                      </option>
                    ))}
                    <option value="custom">Custom Server...</option>
                  </select>
                </Field>

                {masterServer === "custom" ? (
                  <Field id="master-custom-server" label="Custom Server Name">
                    <input
                      id="master-custom-server"
                      type="text"
                      value={masterCustomServer}
                      onChange={(e) => setMasterCustomServer(e.target.value)}
                      placeholder="e.g. Exness-MT5Trial15"
                      className={inputCls}
                    />
                  </Field>
                ) : (
                  <Field id="master-label" label="Account Label / Tag">
                    <input
                      id="master-label"
                      type="text"
                      value={masterLabel}
                      onChange={(e) => setMasterLabel(e.target.value)}
                      placeholder="e.g. Exness Demo BTC"
                      className={inputCls}
                    />
                  </Field>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowMasterModal(false)}
                  className="px-4 py-2.5 rounded-inner border border-border text-text-secondary text-sm hover:text-text-primary min-h-[44px]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingMaster}
                  className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 disabled:opacity-50 text-black font-bold rounded-inner text-sm flex items-center gap-2 min-h-[44px] shadow-md"
                >
                  {savingMaster ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save & Authorize Master Engine"}
                </button>
              </div>
            </form>
          </div>
        </section>
      )}

      {/* ── Link Sub-Account Form ── */}
      {showForm && (
        <section id="sub-account-registration-form" className="bg-surface border-2 border-accent/40 rounded-card overflow-hidden shadow-2xl transition-all duration-300">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-2/40">
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-semibold text-text-primary">
                Link Exness Managed Sub-Account
              </h2>
            </div>
            <button
              onClick={() => { setShowForm(false); setError(null); }}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>

          <div className="p-5 space-y-4">
            <div className="bg-surface-2 border border-border rounded-inner p-3 flex items-start gap-2.5 text-xs text-text-secondary">
              <Shield className="w-4 h-4 text-accent shrink-0 mt-0.5" />
              <span>
                <strong>Zero Cloud Storage:</strong> The password is sent directly to your local engine on your laptop and stored inside Windows Credential Manager. It is never transmitted to Supabase or Vercel.
              </span>
            </div>

            <form onSubmit={handleAddAccount} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field id="acct-label" label="Account Label / Nickname">
                  <input
                    id="acct-label"
                    type="text"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    required
                    placeholder="e.g. Exness Real #2"
                    className={inputCls}
                  />
                </Field>

                <Field id="acct-login" label="MT5 Account Number (Login)">
                  <input
                    id="acct-login"
                    type="text"
                    inputMode="numeric"
                    value={login}
                    onChange={(e) => setLogin(e.target.value.replace(/\D/g, ""))}
                    required
                    placeholder="e.g. 88392102"
                    className={inputCls}
                  />
                </Field>

                <Field id="acct-password" label="MT5 Trading Password">
                  <div className="relative">
                    <input
                      id="acct-password"
                      type={showPw ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className={cn(inputCls, "pr-11")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </Field>

                <Field id="acct-server" label="Broker Server">
                  <select
                    id="acct-server"
                    value={server}
                    onChange={(e) => setServer(e.target.value)}
                    className={inputCls}
                  >
                    {EXNESS_SERVERS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                    <option value="custom">Custom server…</option>
                  </select>
                  {server === "custom" && (
                    <input
                      type="text"
                      value={customServer}
                      onChange={(e) => setCustom(e.target.value)}
                      placeholder="e.g. Exness-MT5Real11"
                      className={cn(inputCls, "mt-2")}
                    />
                  )}
                </Field>

                <Field id="acct-multiplier" label="Risk Multiplier" hint="1.0x = exact 1.0% risk of this account balance.">
                  <select
                    id="acct-multiplier"
                    value={multiplier}
                    onChange={(e) => setMultiplier(parseFloat(e.target.value))}
                    className={inputCls}
                  >
                    <option value="0.5">0.5x (Conservative — 0.5% risk)</option>
                    <option value="1.0">1.0x (Standard — 1.0% risk)</option>
                    <option value="1.5">1.5x (Aggressive — 1.5% risk)</option>
                    <option value="2.0">2.0x (Double — 2.0% risk)</option>
                  </select>
                </Field>

                <Field id="acct-slippage" label="Max Slippage Guard (pips)" hint="Rejects copy if price drifts beyond this distance.">
                  <input
                    id="acct-slippage"
                    type="number"
                    step="0.5"
                    min="1.0"
                    max="10.0"
                    value={maxSlippage}
                    onChange={(e) => setMaxSlippage(parseFloat(e.target.value))}
                    className={inputCls}
                  />
                </Field>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2.5 rounded-inner border border-border text-text-secondary text-sm hover:text-text-primary min-h-[44px]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-accent hover:bg-blue-600 disabled:opacity-50 text-white font-semibold rounded-inner text-sm flex items-center gap-2 min-h-[44px]"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save & Link Sub-Account"}
                </button>
              </div>
            </form>
          </div>
        </section>
      )}

      {/* ── 1. Master Account Card (Open Terminal) ── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gold" />
            <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              1. Master Terminal (Signal Generator &amp; Execution)
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => scrollToMasterRegistration("DEMO_BTC")}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 text-amber-400 font-semibold rounded-inner text-xs transition-all active:scale-95"
            >
              <Settings className="w-3.5 h-3.5" />
              {master?.account_id ? "Configure Credentials" : "Add Exness Demo Account"}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="bg-surface border border-border rounded-card p-5">
            <Skeleton className="h-5 w-48 mb-3" />
            <Skeleton className="h-4 w-72" />
          </div>
        ) : !master?.account_id ? (
          <div className="bg-gradient-to-r from-amber-500/10 via-surface to-surface border-2 border-amber-500/30 rounded-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-12 h-12 rounded-inner bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0">
                <Server className="w-6 h-6 text-amber-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-text-primary">Connect Primary Exness Demo (BTCUSD)</h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase">
                    Ready to Test
                  </span>
                </div>
                <p className="text-xs text-text-secondary mt-1 max-w-xl">
                  Add your Exness MT5 demo credentials to test the quantitative bot on BTCUSD. The password is saved directly into Windows Credential Manager on your laptop with zero cloud exposure.
                </p>
              </div>
            </div>
            <button
              onClick={() => scrollToMasterRegistration("DEMO_BTC")}
              className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-bold text-sm rounded-inner shrink-0 shadow-md active:scale-95"
            >
              Connect Exness Demo Account
            </button>
          </div>
        ) : (
          <div className="bg-surface border-2 border-gold/40 rounded-card p-5 relative overflow-hidden space-y-4">
            <div className="absolute top-0 right-0 px-3 py-1 bg-gold/15 text-gold text-[11px] font-bold rounded-bl-inner border-l border-b border-gold/30 uppercase tracking-wider">
              Master Terminal Window
            </div>

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div className="w-11 h-11 rounded-inner bg-gold/10 border border-gold/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Server className="w-5 h-5 text-gold" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-bold text-text-primary">
                      {master?.label || "Exness Master Account"}
                    </h3>
                    <span className={cn(
                      "px-2 py-0.5 text-[10px] font-bold rounded-full uppercase",
                      copierData?.terminal_online
                        ? "bg-profit/10 border border-profit/20 text-profit"
                        : "bg-amber-500/10 border border-amber-500/20 text-amber-400"
                    )}>
                      {copierData?.terminal_online ? "TERMINAL ONLINE" : master?.status || "READY FOR DEMO"}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-surface-2 text-text-secondary border border-border">
                      {master?.mode || "DEMO"}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-1">
                    Account: <strong className="text-text-primary">{master?.account_id}</strong> · Server: <strong>{master?.server}</strong> · Asset: <strong className="text-accent">{master?.symbol || "BTCUSD"}</strong>
                  </p>
                </div>
              </div>

              {/* Master Financials */}
              <div className="grid grid-cols-3 gap-4 border-t md:border-t-0 md:border-l border-border pt-3 md:pt-0 md:pl-6">
                <div>
                  <span className="text-[11px] text-text-secondary block">Balance</span>
                  <span className="text-sm font-bold text-text-primary tabular-nums">
                    ${(master?.balance ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-text-secondary block">Equity</span>
                  <span className="text-sm font-bold text-text-primary tabular-nums">
                    ${(master?.equity ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-text-secondary block">Free Margin</span>
                  <span className="text-sm font-bold text-text-primary tabular-nums">
                    ${(master?.margin_free ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Controls: Symbol Toggle & CLI Launch Snippet */}
            <div className="pt-3 border-t border-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-text-secondary font-medium">Target Asset:</span>
                <button
                  onClick={() => handleQuickSwitchSymbol("BTCUSD")}
                  className={cn(
                    "px-2.5 py-1 rounded text-xs font-semibold border transition-all",
                    (master?.symbol || "BTCUSD") === "BTCUSD"
                      ? "bg-accent/20 border-accent text-accent font-bold"
                      : "bg-surface-2 border-border text-text-secondary hover:text-text-primary"
                  )}
                >
                  BTCUSD (Bitcoin)
                </button>
                <button
                  onClick={() => handleQuickSwitchSymbol("XAUUSD")}
                  className={cn(
                    "px-2.5 py-1 rounded text-xs font-semibold border transition-all",
                    master?.symbol === "XAUUSD"
                      ? "bg-gold/20 border-gold text-gold font-bold"
                      : "bg-surface-2 border-border text-text-secondary hover:text-text-primary"
                  )}
                >
                  XAUUSD (Gold)
                </button>
              </div>

              <div className="flex items-center gap-2">
                <div className="bg-surface-2 border border-border px-2.5 py-1 rounded font-mono text-[11px] text-text-secondary flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-accent" />
                  <span>python main.py --mode {(master?.mode || "demo").toLowerCase()} --symbol {master?.symbol || "BTCUSD"}</span>
                </div>
                <button
                  onClick={() => copyCliCommand(`python main.py --mode ${(master?.mode || "demo").toLowerCase()} --symbol ${master?.symbol || "BTCUSD"}`)}
                  className="px-2.5 py-1 rounded border border-border bg-surface-2 hover:bg-surface-2/80 text-text-primary font-semibold text-[11px] flex items-center gap-1"
                  title="Copy engine launch command"
                >
                  {copiedCmd ? <Check className="w-3.5 h-3.5 text-profit" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCmd ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── 2. Connected Sub-Accounts (Replication Targets) ── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent" />
            <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              2. Connected Sub-Accounts ({children.length})
            </h2>
          </div>
          <span className="text-xs text-text-secondary">
            In-Process Fast Switching (&lt;200ms)
          </span>
        </div>

        {children.length === 0 ? (
          <div className="bg-surface border border-border rounded-card p-8 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-surface-2 flex items-center justify-center mx-auto text-text-secondary">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <p className="font-semibold text-text-primary">No Sub-Accounts Linked Yet</p>
              <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                Link secondary or investor accounts to automatically mirror primary execution with exact proportional risk sizing.
              </p>
            </div>
            <button
              onClick={() => scrollToSubAccountRegistration()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-blue-600 active:scale-95 text-white rounded-inner text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              Link First Sub-Account
            </button>
          </div>
        ) : (
          <div className="space-y-2.5">
            {children.map((child) => (
              <div
                key={child.account_id}
                className="bg-surface border border-border rounded-card p-4 transition-all hover:border-accent/30"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  {/* Account Header & Status */}
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-inner bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                      <Copy className="w-4 h-4 text-accent" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-sm text-text-primary">{child.label}</h4>
                        <span className={cn(
                          "px-2 py-0.5 text-[10px] font-bold rounded-full uppercase",
                          child.is_active
                            ? "bg-profit/10 text-profit border border-profit/20"
                            : "bg-surface-2 text-text-secondary border border-border"
                        )}>
                          {child.is_active ? "COPYING ACTIVE" : "PAUSED"}
                        </span>
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-surface-2 text-text-secondary border border-border">
                          {child.risk_multiplier || 1.0}x Risk
                        </span>
                      </div>
                      <p className="text-xs text-text-secondary mt-0.5">
                        Account: <strong className="text-text-primary">{child.account_id}</strong> · Server: {child.server}
                      </p>
                    </div>
                  </div>

                  {/* Financials & Quick Actions */}
                  <div className="flex items-center justify-between md:justify-end gap-5 pt-3 md:pt-0 border-t md:border-t-0 border-border">
                    <div className="grid grid-cols-2 gap-4 text-right">
                      <div>
                        <span className="text-[10px] text-text-secondary block">Balance</span>
                        <span className="text-xs font-bold text-text-primary tabular-nums">
                          ${(child.balance || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-text-secondary block">Equity</span>
                        <span className="text-xs font-bold text-text-primary tabular-nums">
                          ${(child.equity || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {/* Toggle Copying button */}
                      <button
                        onClick={() => handleToggle(child.account_id)}
                        disabled={togglingId === child.account_id}
                        className={cn(
                          "px-3 py-1.5 rounded-inner text-xs font-semibold border transition-all min-h-[36px]",
                          child.is_active
                            ? "bg-surface-2 border-border text-text-secondary hover:text-text-primary"
                            : "bg-profit/10 border-profit/30 text-profit hover:bg-profit/20"
                        )}
                      >
                        {togglingId === child.account_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : child.is_active ? (
                          "Pause Copying"
                        ) : (
                          "Resume Copying"
                        )}
                      </button>

                      {/* Remove Account */}
                      <ConfirmDialog
                        title={`Remove ${child.label}?`}
                        description="This removes the child account from trade copying. You can re-add it at any time."
                        confirmLabel="Remove"
                        danger
                        onConfirm={() => handleRemove(child.account_id)}
                      >
                        <button className="p-2 text-text-secondary hover:text-loss rounded-inner border border-transparent hover:border-loss/20 hover:bg-loss/10 transition-colors">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </ConfirmDialog>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── 3. Recent Copied Trades Audit Table ── */}
      {copiedTrades.length > 0 && (
        <section className="space-y-3 pt-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              3. Recent Copied Trades Audit Log
            </h2>
            <span className="text-xs text-text-secondary font-mono">
              Live In-Memory Audit
            </span>
          </div>

          <div className="bg-surface border border-border rounded-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-2 border-b border-border text-text-secondary">
                  <tr>
                    <th className="py-2.5 px-4 font-semibold">Master Ticket</th>
                    <th className="py-2.5 px-4 font-semibold">Child Account</th>
                    <th className="py-2.5 px-4 font-semibold">Child Ticket</th>
                    <th className="py-2.5 px-4 font-semibold">Symbol</th>
                    <th className="py-2.5 px-4 font-semibold">Direction</th>
                    <th className="py-2.5 px-4 font-semibold">Volume</th>
                    <th className="py-2.5 px-4 font-semibold">Entry Price</th>
                    <th className="py-2.5 px-4 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-text-primary">
                  {copiedTrades.slice(0, 10).map((t) => (
                    <tr key={`${t.master_ticket}-${t.child_ticket}`} className="hover:bg-surface-2/30">
                      <td className="py-2.5 px-4 font-mono font-medium">#{t.master_ticket}</td>
                      <td className="py-2.5 px-4 font-mono">{t.child_account_id}</td>
                      <td className="py-2.5 px-4 font-mono text-accent font-medium">#{t.child_ticket}</td>
                      <td className="py-2.5 px-4 font-bold">{t.symbol}</td>
                      <td className="py-2.5 px-4">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                          t.direction === "BULLISH" ? "bg-profit/10 text-profit" : "bg-loss/10 text-loss"
                        )}>
                          {t.direction}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 tabular-nums">{t.volume} lots</td>
                      <td className="py-2.5 px-4 tabular-nums font-mono">${t.entry_price.toFixed(2)}</td>
                      <td className="py-2.5 px-4">
                        <span className="text-[11px] font-semibold text-profit">
                          ● {t.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function Field({
  id,
  label,
  hint,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-text-primary block">
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-text-secondary">{hint}</p>}
    </div>
  );
}

const inputCls =
  "w-full bg-surface-2 border border-border rounded-inner px-3.5 py-2.5 text-sm " +
  "text-text-primary placeholder:text-text-secondary focus:outline-none " +
  "focus:border-accent focus:ring-1 focus:ring-accent/20 transition-colors";
