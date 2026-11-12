import { NextResponse } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

interface AccountSetting {
  account_id?: number | string;
  login?: string;
  label?: string;
  server?: string;
  symbol?: string;
  mode?: string;
  is_master?: boolean;
  is_active?: boolean;
  balance?: number;
  equity?: number;
  status?: string;
  risk_multiplier?: number;
}

export async function GET() {
  try {
    const supabaseUrl = getSupabaseUrl();
    const headers     = getServiceHeaders();

    const [hbRes, snapRes, settingsRes] = await Promise.all([
      fetch(`${supabaseUrl}/rest/v1/heartbeats?select=*&order=ts.desc&limit=1`,          { headers, cache: "no-store" }).catch(() => null),
      fetch(`${supabaseUrl}/rest/v1/accounts_snapshot?select=*&order=ts.desc&limit=1`,   { headers, cache: "no-store" }).catch(() => null),
      fetch(`${supabaseUrl}/rest/v1/settings?select=key,value`,                          { headers, cache: "no-store" }).catch(() => null),
    ]);

    let terminalOnline = false;
    let liveEquity  = 0.0;
    let liveBalance = 0.0;
    let liveFreeMargin = 0.0;

    let rows: Array<{ key: string; value: AccountSetting }> = [];
    if (settingsRes?.ok) rows = await settingsRes.json().catch(() => []);

    const acctStateRow = rows.find(r => r.key === "account_state");
    const acctState = acctStateRow?.value as Record<string, unknown> | undefined;
    if (acctState && acctState.connected) {
      terminalOnline = true;
      if (acctState.equity != null) liveEquity = Number(acctState.equity);
      if (acctState.balance != null) liveBalance = Number(acctState.balance);
      if (acctState.free_margin != null) liveFreeMargin = Number(acctState.free_margin);
    }

    if (hbRes?.ok) {
      const hbData = await hbRes.json().catch(() => []);
      if (hbData?.length > 0) {
        const hb = hbData[0];
        const ageMs = Date.now() - new Date(hb.ts).getTime();
        if (hb.mt5_connected && ageMs < 45_000) terminalOnline = true;
        if (liveEquity === 0.0 && hb.equity  != null) liveEquity  = Number(hb.equity);
        if (liveBalance === 0.0 && hb.balance != null) liveBalance = Number(hb.balance);
      }
    }

    if (liveEquity === 0.0 && snapRes?.ok) {
      const snapData = await snapRes.json().catch(() => []);
      if (snapData?.length > 0) {
        if (snapData[0].equity  != null) liveEquity  = Number(snapData[0].equity);
        if (snapData[0].balance != null) liveBalance = Number(snapData[0].balance);
      }
    }

    const masterRow = rows.find(r => r.key === "mt5_account_master" || r.value?.is_master);
    const childRows = rows.filter(r => r !== masterRow && (r.key.startsWith("mt5_account_") || r.value?.account_id));
    const masterVal = masterRow?.value;
    const acctId    = masterVal ? Number(masterVal.account_id || masterVal.login) : 0;

    const master = {
      account_id:  acctId,
      label:       masterVal?.label || (acctId ? `Exness ${masterVal?.mode || "Demo"} #${acctId}` : "Exness Master Terminal"),
      server:      masterVal?.server || "Exness-MT5Trial9",
      balance:     terminalOnline ? liveBalance : (masterVal?.balance ?? 0.0),
      equity:      terminalOnline ? liveEquity  : (masterVal?.equity  ?? 0.0),
      margin_free: terminalOnline ? (liveFreeMargin || liveEquity) : 0.0,
      is_master:   true,
      is_active:   masterVal?.is_active ?? (acctId > 0),
      status:      terminalOnline ? "CONNECTED (LIVE IPC)" : acctId > 0 ? "STANDBY" : "NOT CONFIGURED",
      symbol:      masterVal?.symbol || "XAUUSD",
      mode:        masterVal?.mode   || "DEMO",
    };

    const children = childRows.map(r => {
      const c   = r.value;
      const cId = Number(c.account_id || c.login);
      return {
        account_id:      cId,
        label:           c.label || `Sub-Account #${cId}`,
        server:          c.server || "Exness-MT5Real",
        balance:         c.balance ?? 0.0,
        equity:          c.equity  ?? 0.0,
        margin_free:     c.equity  ?? 0.0,
        is_master:       false,
        is_active:       c.is_active ?? true,
        status:          terminalOnline ? "COPIER READY" : "SAVED",
        risk_multiplier: c.risk_multiplier ?? 1.0,
      };
    });

    return NextResponse.json(
      { terminal_online: terminalOnline, master, children, total_children: children.length, active_children: children.filter(c => c.is_active).length },
      { headers: { "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2" } }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal Server Error" },
      { status: 500 }
    );
  }
}
