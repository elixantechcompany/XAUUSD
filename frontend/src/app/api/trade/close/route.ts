import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ticket, symbol } = body;

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    const cmdPayload = {
      type: "CLOSE_TRADE",
      payload: {
        ticket: ticket ? String(ticket) : undefined,
        symbol: symbol ? String(symbol) : undefined,
        requested_at: new Date().toISOString(),
      },
      status: "pending",
    };

    const res = await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST",
      headers,
      body: JSON.stringify(cmdPayload),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `Close command failed: ${err}` }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      message: `Close order dispatched for position #${ticket || symbol || 'ALL'}`,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Error closing trade";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
