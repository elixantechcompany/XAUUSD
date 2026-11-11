import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  try {
    const body          = await request.json();
    const { ticket, symbol } = body;
    const supabaseUrl   = getSupabaseUrl();
    const headers       = getServiceHeaders();

    const res = await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        type: "CLOSE_TRADE",
        payload: {
          ticket: ticket ? String(ticket) : undefined,
          symbol: symbol ? String(symbol) : undefined,
          requested_at: new Date().toISOString(),
        },
        status: "pending",
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `Close command failed: ${err}` }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      message: `Close order dispatched for position #${ticket || symbol || "ALL"}`,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Error closing trade" },
      { status: 500 }
    );
  }
}
