import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const requestedSymbol = (searchParams.get("symbol") || "BTCUSD").toUpperCase();

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    const res = await fetch(
      `${supabaseUrl}/rest/v1/settings?select=value,updated_at&key=eq.live_market_data&limit=1`,
      { headers, cache: "no-store" }
    );

    if (res.ok) {
      const rows = await res.json();
      if (rows && rows.length > 0 && rows[0].value) {
        const val = rows[0].value;
        const symData = val[requestedSymbol] || (requestedSymbol === "XAUUSD" ? val.XAUUSD : val.BTCUSD);
        return NextResponse.json(
          {
            success: true,
            symbol: requestedSymbol,
            bot_status: val.bot_status || "BOT RUNNING · ANALYZING MARKET",
            bot_state: val.bot_state || "ANALYZING",
            reasoning: val.reasoning || "Autonomous quantitative SMC analysis active.",
            updated_at: val.updated_at || rows[0].updated_at,
            data: symData,
          },
          {
            headers: {
              "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2",
            },
          }
        );
      }
    }

    // Fallback if DB record not ready
    return NextResponse.json({
      success: true,
      symbol: requestedSymbol,
      bot_status: "BOT RUNNING · ANALYZING MARKET",
      bot_state: "ANALYZING",
      reasoning: "Scanning H1 Market Structure and Fair Value Gaps via MT5 IPC.",
      updated_at: new Date().toISOString(),
      data: null,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Error fetching market data";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
