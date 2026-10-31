import { NextResponse } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

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
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    // 1. Fetch heartbeat, snapshot and settings concurrently in parallel (3x faster)
    const [hbRes, snapRes, settingsRes] = await Promise.all([
      fetch(`${supabaseUrl}/rest/v1/heartbeats?select=*&order=ts.desc&limit=1`, { headers, cache: "no-store" }).catch(() => null),
      fetch(`${supabaseUrl}/rest/v1/accounts_snapshot?select=*&order=ts.desc&limit=1`, { headers, cache: "no-store" }).catch(() => null),
      fetch(`${supabaseUrl}/rest/v1/settings?select=key,value&key=like.mt5_account_*`, { headers, cache: "no-store" }).catch(() => null),
    ]);

    let terminalOnline = false;
    let liveEquity = 0.0;
    let liveBalance = 0.0;

    if (hbRes && hbRes.ok) {
      try {
        const hbData = await hbRes.json();
        if (hbData && hbData.length > 0) {
          const hb = hbData[0];
          const ageMs = Date.now() - new Date(hb.ts).getTime();
          if (hb.mt5_connected && ageMs < 45_000) {
            terminalOnline = true;
          }
          if (hb.equity != null) liveEquity = Number(hb.equity);
          if (hb.balance != null) liveBalance = Number(hb.balance);
        }
      } catch {
        // ignore
      }
    }

    if (liveEquity === 0.0 && snapRes && snapRes.ok) {
      try {
        const snapData = await snapRes.json();
        if (snapData && snapData.length > 0) {
          if (snapData[0].equity != null) liveEquity = Number(snapData[0].equity);
          if (snapData[0].balance != null) liveBalance = Number(snapData[0].balance);
        }
      } catch {
        // ignore
      }
    }

    let rows: Array<{ key: string; value: AccountSetting }> = [];
    if (settingsRes && settingsRes.ok) {
      try {
        rows = await settingsRes.json();
      } catch {
        // ignore
      }
    }

    const masterRow = rows.find(
      (r) => r.key === "mt5_account_master" || r.value?.is_master
    );
    const childRows = rows.filter((r) => r !== masterRow);

    const masterVal = masterRow?.value;
    const acctId = masterVal ? Number(masterVal.account_id || masterVal.login) : 0;

    const master = {
      account_id: acctId,
      label: masterVal?.label || (acctId ? `Exness ${masterVal?.mode || "Demo"} #${acctId}` : "Exness Master Terminal"),
      server: masterVal?.server || "Exness-MT5Trial9",
      balance: terminalOnline ? liveBalance : (masterVal?.balance ?? 0.0),
      equity: terminalOnline ? liveEquity : (masterVal?.equity ?? 0.0),
      margin_free: terminalOnline ? liveEquity : 0.0,
      is_master: true,
      is_active: masterVal?.is_active ?? (acctId > 0),
      status: terminalOnline
        ? "CONNECTED (LIVE IPC)"
        : acctId > 0
        ? "STANDBY (READY ON LAPTOP)"
        : "NOT CONFIGURED",
      symbol: masterVal?.symbol || "BTCUSD",
      mode: masterVal?.mode || "DEMO",
    };

    const children = childRows.map((r) => {
      const c = r.value;
      const cId = Number(c.account_id || c.login);
      return {
        account_id: cId,
        label: c.label || `Sub-Account #${cId}`,
        server: c.server || "Exness-MT5Real",
        balance: c.balance ?? 0.0,
        equity: c.equity ?? 0.0,
        margin_free: c.equity ?? 0.0,
        is_master: false,
        is_active: c.is_active ?? true,
        status: terminalOnline ? "COPIER READY" : "SAVED",
        risk_multiplier: c.risk_multiplier ?? 1.0,
      };
    });

    return NextResponse.json(
      {
        terminal_online: terminalOnline,
        master,
        children,
        total_children: children.length,
        active_children: children.filter((c) => c.is_active).length,
      },
      {
        headers: {
          "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2",
        },
      }
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
