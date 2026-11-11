import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { account_id, server, label, symbol = "BTCUSD", mode = "DEMO", password } = body;

    const acctId = Number(account_id);
    if (!acctId || isNaN(acctId)) {
      return NextResponse.json({ error: "Valid numeric Exness Account Number is required." }, { status: 400 });
    }
    if (!server) {
      return NextResponse.json({ error: "Exness MT5 Server is required." }, { status: 400 });
    }

    const supabaseUrl = getSupabaseUrl();
    const headers     = { ...getServiceHeaders(), Prefer: "resolution=merge-duplicates" };

    await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST", headers,
      body: JSON.stringify({
        key: "mt5_account_master",
        value: {
          account_id: acctId, login: acctId.toString(),
          label: label || `Exness ${mode} #${acctId}`,
          server, symbol, mode,
          is_master: true, is_active: true,
          status: "STANDBY",
          updated_at: new Date().toISOString(),
        },
        updated_at: new Date().toISOString(),
      }),
    });

    await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST", headers,
      body: JSON.stringify({
        key: "mt5_active_symbol",
        value: { symbol },
        updated_at: new Date().toISOString(),
      }),
    });

    await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST",
      headers: getServiceHeaders(),
      body: JSON.stringify({
        type: "CONFIGURE_MASTER",
        payload: {
          account_id: acctId, server, symbol, mode,
          password: password ? "SAVED_LOCAL" : undefined,
        },
        status: "pending",
      }),
    }).catch(() => null);

    return NextResponse.json({
      success: true,
      message: `Exness ${mode} Account #${acctId} configured for ${symbol}.`,
      account: { account_id: acctId, server, symbol, mode, label: label || `Exness ${mode} #${acctId}` },
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal Server Error" },
      { status: 500 }
    );
  }
}
