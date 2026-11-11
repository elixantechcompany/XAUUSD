import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const requestedSymbol = (searchParams.get("symbol") || "BTCUSD").toUpperCase();

    const supabaseUrl = getSupabaseUrl();
    const headers     = getServiceHeaders();

    const res = await fetch(
      `${supabaseUrl}/rest/v1/settings?select=value,updated_at&key=eq.live_market_data&limit=1`,
      { headers, cache: "no-store" }
    );

    if (res.ok) {
      const rows = await res.json();
      if (rows?.length > 0 && rows[0].value) {
        const val = rows[0].value;
        const symData = val[requestedSymbol] || null;
        return NextResponse.json(
          {
            success: true,
            symbol: requestedSymbol,
            bot_status: val.bot_status || "BOT RUNNING · ANALYZING MARKET",
            bot_state: val.bot_state || "ANALYZING",
            reasoning: val.reasoning || "Autonomous quantitative SMC analysis active.",
            updated_at: val.updated_at || rows[0].updated_at,
            open_positions: val.open_positions || [],
            data: symData,
          },
          { headers: { "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0" } }
        );
      }
    }

    return NextResponse.json({
      success: true,
      symbol: requestedSymbol,
      bot_status: "BOT RUNNING · ANALYZING MARKET",
      bot_state: "ANALYZING",
      reasoning: "Scanning H1 Market Structure and Fair Value Gaps via MT5 IPC.",
      updated_at: new Date().toISOString(),
      open_positions: [],
      data: null,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Error fetching market data" },
      { status: 500 }
    );
  }
}
