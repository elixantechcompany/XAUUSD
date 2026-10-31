import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { account_id, server, label, symbol = "BTCUSD", mode = "DEMO", password } = body;

    const acctId = Number(account_id);
    if (!acctId || isNaN(acctId)) {
      return NextResponse.json(
        { error: "Valid numeric Exness Account Number / MT5 Login is required." },
        { status: 400 }
      );
    }
    if (!server) {
      return NextResponse.json(
        { error: "Exness MT5 Server is required (e.g. Exness-MT5Trial9 or Exness-MT5Real)." },
        { status: 400 }
      );
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
    };

    // 1. Upsert master account into Supabase settings
    const masterPayload = {
      key: "mt5_account_master",
      value: {
        account_id: acctId,
        login: acctId.toString(),
        label: label || `Exness ${mode} #${acctId}`,
        server,
        symbol,
        mode,
        is_master: true,
        is_active: true,
        status: "STANDBY (READY ON LAPTOP)",
        updated_at: new Date().toISOString(),
      },
      updated_at: new Date().toISOString(),
    };

    const upsertRes = await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST",
      headers,
      body: JSON.stringify(masterPayload),
    });

    if (!upsertRes.ok) {
      const errText = await upsertRes.text();
      return NextResponse.json(
        { error: `Database error saving account: ${errText}` },
        { status: 500 }
      );
    }

    // 2. Upsert active symbol
    await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        key: "mt5_active_symbol",
        value: { symbol },
        updated_at: new Date().toISOString(),
      }),
    });

    // 3. Dispatch CONFIGURE_MASTER command for local python bot
    await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        type: "CONFIGURE_MASTER",
        payload: {
          account_id: acctId,
          server,
          symbol,
          mode,
          password: password ? "SAVED_LOCAL" : undefined,
        },
        status: "pending",
      }),
    }).catch(() => null);

    return NextResponse.json({
      success: true,
      message: `Exness ${mode} Account #${acctId} configured for ${symbol} successfully!`,
      account: {
        account_id: acctId,
        server,
        symbol,
        mode,
        label: label || `Exness ${mode} #${acctId}`,
      },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
