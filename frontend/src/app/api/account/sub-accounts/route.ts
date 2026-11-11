import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { account_id, label, server, risk_multiplier = 1.0, is_active = true, password } = body;

    const acctId = Number(account_id);
    if (!acctId || isNaN(acctId)) {
      return NextResponse.json({ error: "Numeric account ID is required." }, { status: 400 });
    }
    if (!server) {
      return NextResponse.json({ error: "Exness server is required." }, { status: 400 });
    }

    const normalizedServer = server.trim().replace(/^Exness\s+/i, "Exness-");
    const supabaseUrl      = getSupabaseUrl();
    const headers          = { ...getServiceHeaders(), Prefer: "resolution=merge-duplicates" };

    const res = await fetch(`${supabaseUrl}/rest/v1/settings`, {
      method: "POST", headers,
      body: JSON.stringify({
        key: `mt5_account_${acctId}`,
        value: {
          account_id: acctId, login: acctId.toString(),
          label:            label || `Sub-Account #${acctId}`,
          server:           normalizedServer,
          risk_multiplier:  Number(risk_multiplier) || 1.0,
          is_master:        false,
          is_active,
          has_password:     Boolean(password),
          created_at:       new Date().toISOString(),
        },
        updated_at: new Date().toISOString(),
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `Database error: ${err}` }, { status: 500 });
    }

    if (password) {
      await fetch(`${supabaseUrl}/rest/v1/commands`, {
        method: "POST",
        headers: getServiceHeaders(),
        body: JSON.stringify({
          type: "REGISTER_CHILD_ACCOUNT",
          payload: {
            account_id: acctId, password: String(password),
            server: normalizedServer,
            label: label || `Sub-Account #${acctId}`,
            risk_multiplier: Number(risk_multiplier) || 1.0,
            is_active,
          },
          status: "pending",
        }),
      }).catch(() => null);
    }

    return NextResponse.json({
      success: true,
      message: `Sub-Account ${label || acctId} registered.`,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal Server Error" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const accountId = searchParams.get("account_id");
    if (!accountId) {
      return NextResponse.json({ error: "account_id parameter is required." }, { status: 400 });
    }

    const supabaseUrl = getSupabaseUrl();
    const headers     = getServiceHeaders();

    const res = await fetch(
      `${supabaseUrl}/rest/v1/settings?key=eq.mt5_account_${accountId}`,
      { method: "DELETE", headers }
    );

    if (!res.ok) {
      return NextResponse.json({ error: "Failed to delete sub-account." }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: `Sub-account #${accountId} removed.` });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal Server Error" },
      { status: 500 }
    );
  }
}
