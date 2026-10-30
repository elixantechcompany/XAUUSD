"use client";

/**
 * Accounts page — add and manage Exness MT5 accounts.
 *
 * Security model (important):
 *   – MT5 trading passwords are NEVER stored in Supabase, Vercel, or the browser.
 *   – Login ID, server name, label, and mode are stored in the Supabase `settings`
 *     table (authenticated, RLS-protected).
 *   – The password is submitted only once, sent directly to the LOCAL engine API
 *     running on the user's machine, and stored in Windows Credential Manager.
 *   – If the engine is offline the password cannot be saved — the user is told why.
 */

import { useEffect, useState, type FormEvent } from "react";
import { getSupabaseClient } from "@/lib/supabase/client";
import { useBotStore } from "@/lib/store";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  Plus, Server, Shield, Eye, EyeOff,
  CheckCircle2, AlertCircle, ChevronDown, ChevronUp,
  Loader2,
} from "lucide-react";

const EXNESS_SERVERS = [
  "Exness-MT5Real",
  "Exness-MT5Real2",
  "Exness-MT5Real3",
  "Exness-MT5Trial",
  "Exness-MT5Demo",
];

interface SavedAccount {
  label: string;
  login: string;
  server: string;
  mode: "paper" | "demo";
  created_at: string;
}

export default function AccountsPage() {
  const heartbeat    = useBotStore((s) => s.heartbeat);
  const engineOnline =
    heartbeat != null &&
    (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 < 60;

  // ── Saved accounts ─────────────────────────────────────────────────────────
  const [accounts, setAccounts]       = useState<SavedAccount[]>([]);
  const [loadingAccounts, setLoading] = useState(true);
  const [expanded, setExpanded]       = useState<string | null>(null);

  // ── Form state ─────────────────────────────────────────────────────────────
  const [showForm, setShowForm]   = useState(false);
  const [label, setLabel]         = useState("");
  const [login, setLogin]         = useState("");
  const [password, setPassword]   = useState("");
  const [server, setServer]       = useState(EXNESS_SERVERS[0]);
  const [customServer, setCustom] = useState("");
  const [mode, setMode]           = useState<"paper" | "demo">("paper");
  const [showPw, setShowPw]       = useState(false);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [success, setSuccess]     = useState<string | null>(null);

  const finalServer = server === "custom" ? customServer.trim() : server;

  // ── Load saved accounts from Supabase on mount ─────────────────────────────
  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const { data, error } = await getSupabaseClient()
          .from("settings")
          .select("key, value")
          .like("key", "mt5_account_%");
        if (error) throw error;
        const loaded: SavedAccount[] = (data ?? [])
          .map((row) => row.value as SavedAccount)
          .filter(Boolean)
          .sort((a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
        setAccounts(loaded);
      } catch {
        // Non-fatal — just show empty state
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ── Save account ───────────────────────────────────────────────────────────
  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!label || !login || !password || !finalServer) {
      return setError("All fields are required.");
    }
    if (!engineOnline) {
      return setError(
        "The engine is offline. Your password cannot be saved securely. " +
          "Start the engine on your laptop, then try again."
      );
    }
    setSaving(true);
    setError(null);

    try {
      // 1. Save non-sensitive metadata to Supabase (label, login, server, mode)
      const { error: dbErr } = await getSupabaseClient()
        .from("settings")
        .upsert(
          {
            key: `mt5_account_${login}`,
            value: {
              label,
              login,
              server: finalServer,
              mode,
              created_at: new Date().toISOString(),
            },
            updated_at: new Date().toISOString(),
          },
          { onConflict: "key" }
        );
      if (dbErr) throw dbErr;

      // 2. Send the password ONLY to the local engine (never to Supabase)
      const engineUrl =
        process.env.NEXT_PUBLIC_ENGINE_API_URL ?? "http://127.0.0.1:8000";
      const res = await fetch(`${engineUrl}/accounts/credential`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password, server: finalServer }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          (body as { detail?: string }).detail ?? `Engine returned ${res.status}`
        );
      }

      // 3. Clear password from memory immediately
      setPassword("");
      setSuccess(
        `${label} saved. Password stored securely on the engine machine only.`
      );
      setShowForm(false);
      setLabel(""); setLogin(""); setCustom("");
      setServer(EXNESS_SERVERS[0]); setMode("paper");

      // 4. Update local list
      const newAcct: SavedAccount = {
        label,
        login,
        server: finalServer,
        mode,
        created_at: new Date().toISOString(),
      };
      setAccounts((prev) => [
        newAcct,
        ...prev.filter((a) => a.login !== login),
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save account.");
    } finally {
      setSaving(false);
    }
  }

  async function removeAccount(acct: SavedAccount) {
    await getSupabaseClient()
      .from("settings")
      .delete()
      .eq("key", `mt5_account_${acct.login}`);
    setAccounts((prev) => prev.filter((a) => a.login !== acct.login));
    if (expanded === acct.login) setExpanded(null);
  }

  function cancelForm() {
    setLabel(""); setLogin(""); setPassword(""); setCustom("");
    setServer(EXNESS_SERVERS[0]); setMode("paper");
    setShowForm(false); setError(null);
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 max-w-2xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">MT5 Accounts</h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Connect your Exness account to enable the trading engine.
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => { setSuccess(null); setShowForm(true); }}
            className="flex items-center gap-1.5 bg-accent text-white text-sm font-semibold px-4 py-2.5 rounded-inner hover:bg-blue-600 active:scale-[0.98] transition-all min-h-[44px] shrink-0"
          >
            <Plus className="w-4 h-4" aria-hidden />
            Add Account
          </button>
        )}
      </div>

      {/* Engine offline warning */}
      {!engineOnline && (
        <div className="bg-warning/10 border border-warning/30 rounded-card p-4 text-sm text-warning flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
          <div>
            <p className="font-medium">Engine is offline</p>
            <p className="text-warning/80 text-xs mt-0.5">
              You can view saved accounts but saving a new MT5 password requires
              the engine to be running on your laptop or VPS.
            </p>
          </div>
        </div>
      )}

      {/* Success */}
      {success && (
        <div className="bg-profit/10 border border-profit/20 rounded-card p-4 text-sm text-profit flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
          <span>{success}</span>
        </div>
      )}

      {/* ── Add account form ──────────────────────────────────────────────── */}
      {showForm && (
        <section className="bg-surface border border-border rounded-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h2 className="text-sm font-semibold text-text-primary">
              Add Exness MT5 Account
            </h2>
            <button
              onClick={cancelForm}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>

          <div className="p-5 space-y-5">
            {/* Security note */}
            <div className="bg-surface-2 border border-border rounded-inner p-3 flex items-start gap-2.5 text-xs text-text-secondary">
              <Shield className="w-4 h-4 shrink-0 mt-0.5 text-accent" aria-hidden />
              <span>
                Your MT5 password goes directly to the engine on your machine and is
                stored in Windows Credential Manager. It is{" "}
                <strong className="text-text-primary">never</strong> sent to Supabase,
                Vercel, or stored in this browser.
              </span>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-loss/10 border border-loss/20 rounded-inner p-3 text-sm text-loss flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-4" noValidate>
              {/* Display label */}
              <Field
                id="acct-label"
                label="Display label"
                hint="A name to identify this account in your dashboard."
              >
                <input
                  id="acct-label"
                  type="text"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  required
                  placeholder="e.g. Exness Standard Live"
                  className={inputCls}
                />
              </Field>

              {/* Login number */}
              <Field
                id="acct-login"
                label="MT5 Login number"
                hint="Find this in your Exness Member Area → My Accounts."
              >
                <input
                  id="acct-login"
                  type="text"
                  inputMode="numeric"
                  value={login}
                  onChange={(e) => setLogin(e.target.value.replace(/\D/g, ""))}
                  required
                  placeholder="e.g. 12345678"
                  className={inputCls}
                />
              </Field>

              {/* Trading password */}
              <Field
                id="acct-password"
                label="MT5 Trading password"
                hint="Use the Trading password, not the Investor password. Sent only to your local engine."
              >
                <div className="relative">
                  <input
                    id="acct-password"
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="off"
                    placeholder="••••••••"
                    className={cn(inputCls, "pr-11")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                    aria-label={showPw ? "Hide password" : "Show password"}
                  >
                    {showPw
                      ? <EyeOff className="w-4 h-4" aria-hidden />
                      : <Eye className="w-4 h-4" aria-hidden />}
                  </button>
                </div>
              </Field>

              {/* Broker server */}
              <Field
                id="acct-server"
                label="Broker server"
                hint="Check your MT5 terminal login screen for the exact name."
              >
                <select
                  id="acct-server"
                  value={server}
                  onChange={(e) => setServer(e.target.value)}
                  className={inputCls}
                >
                  {EXNESS_SERVERS.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                  <option value="custom">Custom server name…</option>
                </select>
                {server === "custom" && (
                  <input
                    type="text"
                    value={customServer}
                    onChange={(e) => setCustom(e.target.value)}
                    placeholder="e.g. Exness-MT5Real4"
                    className={cn(inputCls, "mt-2")}
                  />
                )}
              </Field>

              {/* Trading mode */}
              <div className="space-y-1.5">
                <span className="text-sm font-medium text-text-primary">Trading mode</span>
                <div className="grid grid-cols-2 gap-2">
                  {(["paper", "demo"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMode(m)}
                      className={cn(
                        "py-2.5 px-3 rounded-inner text-sm font-medium transition-all min-h-[44px] border",
                        mode === m
                          ? "bg-accent text-white border-accent"
                          : "bg-surface-2 border-border text-text-secondary hover:text-text-primary hover:border-accent/40"
                      )}
                    >
                      {m === "paper" ? "📄  Paper only" : "🔬  Demo (MT5)"}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-text-secondary">
                  Paper: bot logic runs but no real MT5 orders. Demo: real orders on an
                  Exness demo account. Live trading is disabled in this release.
                </p>
              </div>

              <button
                type="submit"
                disabled={saving || !label || !login || !password || !finalServer}
                className="w-full bg-accent hover:bg-blue-600 disabled:opacity-50 text-white font-semibold py-3 rounded-inner text-sm transition-all active:scale-[0.99] min-h-[44px] flex items-center justify-center gap-2"
              >
                {saving
                  ? <><Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Saving…</>
                  : "Save account"}
              </button>
            </form>
          </div>
        </section>
      )}

      {/* ── Account list ──────────────────────────────────────────────────── */}
      {loadingAccounts ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-card p-4">
              <Skeleton className="h-4 w-40 mb-2" />
              <Skeleton className="h-3 w-56" />
            </div>
          ))}
        </div>
      ) : accounts.length === 0 && !showForm ? (
        <div className="bg-surface border border-border rounded-card p-8 text-center space-y-4">
          <div className="w-12 h-12 bg-surface-2 rounded-xl flex items-center justify-center mx-auto">
            <Server className="w-6 h-6 text-text-secondary" aria-hidden />
          </div>
          <div>
            <p className="text-text-primary font-medium">No accounts added yet</p>
            <p className="text-text-secondary text-sm mt-1">
              Add your Exness account to connect the bot engine to MT5.
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 bg-accent text-white text-sm font-semibold px-5 py-2.5 rounded-inner hover:bg-blue-600 transition-all min-h-[44px]"
          >
            <Plus className="w-4 h-4" aria-hidden />
            Add MT5 Account
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {accounts.map((acct) => (
            <div
              key={acct.login}
              className="bg-surface border border-border rounded-card overflow-hidden"
            >
              {/* Row */}
              <button
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-surface-2/40 transition-colors"
                onClick={() =>
                  setExpanded(expanded === acct.login ? null : acct.login)
                }
                aria-expanded={expanded === acct.login}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 bg-accent/10 border border-accent/20 rounded-inner flex items-center justify-center shrink-0">
                    <Server className="w-4 h-4 text-accent" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-text-primary font-medium text-sm truncate">
                      {acct.label}
                    </p>
                    <p className="text-text-secondary text-xs truncate">
                      {acct.login} · {acct.server}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2.5 shrink-0 ml-3">
                  <span
                    className={cn(
                      "text-xs px-2 py-0.5 rounded-full font-medium uppercase tracking-wide",
                      acct.mode === "paper"
                        ? "bg-accent/10 text-accent"
                        : "bg-warning/10 text-warning"
                    )}
                  >
                    {acct.mode}
                  </span>
                  {expanded === acct.login ? (
                    <ChevronUp className="w-4 h-4 text-text-secondary" aria-hidden />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-text-secondary" aria-hidden />
                  )}
                </div>
              </button>

              {/* Expanded detail */}
              {expanded === acct.login && (
                <div className="border-t border-border bg-surface-2/50 px-5 py-4 space-y-4">
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                    <div>
                      <dt className="text-xs text-text-secondary mb-0.5">Login</dt>
                      <dd className="text-text-primary font-medium tabular-nums">
                        {acct.login}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary mb-0.5">Server</dt>
                      <dd className="text-text-primary font-medium truncate">
                        {acct.server}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary mb-0.5">Mode</dt>
                      <dd className="text-text-primary font-medium capitalize">
                        {acct.mode}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-text-secondary mb-0.5">Password</dt>
                      <dd className="text-text-secondary text-xs">
                        Stored in engine only
                      </dd>
                    </div>
                  </dl>
                  <ConfirmDialog
                    title={`Remove ${acct.label}?`}
                    description="This removes the account from your dashboard. The password stored on the engine machine will need to be cleared separately."
                    confirmLabel="Remove account"
                    danger
                    onConfirm={() => removeAccount(acct)}
                  >
                    <button className="text-xs px-3 py-2 bg-loss/10 border border-loss/20 text-loss rounded-inner hover:bg-loss/20 transition-colors min-h-[44px]">
                      Remove
                    </button>
                  </ConfirmDialog>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-text-secondary pb-4">
        MT5 credentials are stored only on your machine. This dashboard stores the
        account label, login number, and server name only.
      </p>
    </div>
  );
}

// ── Small reusable field wrapper ──────────────────────────────────────────────
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
      <label htmlFor={id} className="text-sm font-medium text-text-primary block">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-text-secondary">{hint}</p>}
    </div>
  );
}

const inputCls =
  "w-full bg-surface-2 border border-border rounded-inner px-4 py-3 text-sm " +
  "text-text-primary placeholder:text-text-secondary focus:outline-none " +
  "focus:border-accent focus:ring-1 focus:ring-accent/20 transition-colors";
