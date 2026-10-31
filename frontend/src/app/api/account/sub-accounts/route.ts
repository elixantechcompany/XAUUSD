import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { account_id, label, server, risk_multiplier = 1.0, is_active = true } = body;

    const acctId = Number(account_id);
    if (!acctId || isNaN(acctId)) {
      return NextResponse.json({ error: "Numeric account ID is required." }, { status: 400 });
    }
    if (!server) {
      return NextResponse.json({ error: "Exness server is required." }, { status: 400 });
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
    };

    const subPayload = {
      key: `mt5_account_${acctId}`,
      value: {
        account_id: acctId,
        login: acctId.toString(),
        label: label || `Sub-Account #${acctId}`,
        server,
        risk_multiplier: Number(risk_multiplier) || 1.0,
        is_master: false,
        is_active,
        created_at: new Date().toISOString(),
      },
      updated_at: new Date().toISOString(),
    };

    const res = await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST",
      headers,
      body: JSON.stringify(subPayload),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `Database error: ${err}` }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      message: `Sub-Account ${label || acctId} registered successfully!`,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const accountId = searchParams.get("account_id");

    if (!accountId) {
      return NextResponse.json({ error: "account_id parameter is required." }, { status: 400 });
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const res = await fetch(
      `${supabaseUrl}/rest/v1/settings?key=eq.mt5_account_${accountId}`,
      {
        method: "DELETE",
        headers: {
          apikey: serviceKey,
          Authorization: `Bearer ${serviceKey}`,
        },
      }
    );

    if (!res.ok) {
      return NextResponse.json({ error: "Failed to delete sub-account." }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: `Sub-account #${accountId} removed.` });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
