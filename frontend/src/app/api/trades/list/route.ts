import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit      = searchParams.get("limit") || "100";
    const instrument = searchParams.get("instrument");

    const supabaseUrl = getSupabaseUrl();
    const headers     = getServiceHeaders();

    let url = `${supabaseUrl}/rest/v1/trades?select=*&order=open_time.desc&limit=${limit}`;
    if (instrument) url += `&instrument=eq.${encodeURIComponent(instrument.toUpperCase())}`;

    const [res, marketRes] = await Promise.all([
      fetch(url, { headers, cache: "no-store" }),
      fetch(`${supabaseUrl}/rest/v1/settings?key=eq.live_market_data`, {
        headers, cache: "no-store",
      }).catch(() => null),
    ]);

    if (!res.ok) return NextResponse.json({ trades: [] });

    let trades = await res.json();

    if (marketRes?.ok) {
      try {
        const marketData = await marketRes.json();
        const livePositions = marketData?.[0]?.value?.open_positions || [];
        trades = trades.map((t: Record<string, unknown>) => {
          if (!t.close_time) {
            const live = livePositions.find(
              (p: Record<string, unknown>) => String(p.ticket) === String(t.ticket)
            );
            if (live) {
              return {
                ...t,
                pnl: live.profit != null ? Number(live.profit) : t.pnl,
                sl:  live.sl != null && Number(live.sl) > 0 ? Number(live.sl) : t.sl,
                tp:  live.tp != null && Number(live.tp) > 0 ? Number(live.tp) : t.tp,
              };
            }
          }
          return t;
        });
      } catch { /* use default */ }
    }

    return NextResponse.json(
      { success: true, trades: trades || [] },
      { headers: { "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2" } }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Error listing trades", trades: [] },
      { status: 500 }
    );
  }
}
