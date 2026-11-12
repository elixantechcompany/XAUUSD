import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

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

    let trades: Record<string, unknown>[] = [];
    if (res.ok) {
      trades = (await res.json()) || [];
    }

    if (marketRes?.ok) {
      try {
        const marketData = await marketRes.json();
        const liveMarketObj = marketData?.[0]?.value || {};
        const livePositions: Record<string, unknown>[] = liveMarketObj.open_positions || [];
        const isMt5Live = Boolean(liveMarketObj.updated_at);
        const liveTickets = new Set(livePositions.map((p) => String(p.ticket)));

        // 1. Reconcile existing DB trades with live MT5 telemetry
        trades = trades.map((t: Record<string, unknown>) => {
          const tTicket = String(t.ticket);
          if (!t.close_time) {
            const live = livePositions.find(
              (p: Record<string, unknown>) => String(p.ticket) === tTicket
            );
            if (live) {
              return {
                ...t,
                pnl: live.profit != null ? Number(live.profit) : t.pnl,
                sl:  live.sl != null && Number(live.sl) > 0 ? Number(live.sl) : t.sl,
                tp:  live.tp != null && Number(live.tp) > 0 ? Number(live.tp) : t.tp,
                open_price: live.price_open != null ? Number(live.price_open) : t.open_price,
                current_price: live.price_current != null ? Number(live.price_current) : t.current_price,
                lots: live.volume != null ? Number(live.volume) : t.lots,
              };
            } else if (isMt5Live) {
              // MT5 is actively reporting but this ticket is NOT in live positions -> it has closed!
              return {
                ...t,
                close_time: new Date().toISOString(),
              };
            }
          }
          return t;
        });

        // 2. Inject any live MT5 open position (e.g. placed from MT5 mobile or pending DB sync)
        const openTicketsInList = new Set(
          trades.filter((t) => !t.close_time).map((t) => String(t.ticket))
        );

        const synthesizedLiveTrades: Record<string, unknown>[] = [];
        for (const p of livePositions) {
          const pTicket = String(p.ticket);
          if (!openTicketsInList.has(pTicket)) {
            const rawSym = String(p.base_symbol || p.symbol || "XAUUSD").toUpperCase();
            const inst = rawSym.includes("BTC") ? "BTCUSD" : "XAUUSD";
            if (instrument && inst !== instrument.toUpperCase()) continue;

            const dirStr = String(p.direction || "BUY").toUpperCase();
            const side = dirStr === "BUY" || dirStr === "BULLISH" ? "BULLISH" : "BEARISH";
            synthesizedLiveTrades.push({
              id: pTicket,
              ticket: pTicket,
              signal_id: null,
              source: String(p.comment || "").includes("SMC") ? "bot" : "mt5_live",
              instrument: inst,
              side,
              lots: Number(p.volume || 0.01),
              open_time: p.open_time ? String(p.open_time) : new Date().toISOString(),
              open_price: Number(p.price_open || 0),
              current_price: Number(p.price_current || p.price_open || 0),
              close_time: null,
              close_price: null,
              sl: p.sl != null && Number(p.sl) > 0 ? Number(p.sl) : null,
              tp: p.tp != null && Number(p.tp) > 0 ? Number(p.tp) : null,
              pnl: Number(p.profit || 0),
              r_multiple: null,
              execution_mode: "demo",
            });
          }
        }

        if (synthesizedLiveTrades.length > 0) {
          trades = [...synthesizedLiveTrades, ...trades];
        }
      } catch { /* use default */ }
    }

    return NextResponse.json(
      { success: true, trades: trades || [] },
      { headers: { "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0" } }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Error listing trades", trades: [] },
      { status: 500 }
    );
  }
}
