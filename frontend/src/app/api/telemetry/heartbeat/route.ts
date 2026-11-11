import { NextResponse } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/**
 * GET /api/telemetry/heartbeat
 *
 * Server-side route that fetches heartbeat + account snapshot + live_market_data
 * from Supabase using the server-side service headers.
 */
export async function GET() {
  try {
    const supabaseUrl = getSupabaseUrl();
    const headers = getServiceHeaders();

    // Fetch heartbeat, snapshot, and live_market_data concurrently
    const [hbRes, snapRes, marketRes] = await Promise.all([
      fetch(
        `${supabaseUrl}/rest/v1/heartbeats?select=*&order=ts.desc&limit=1`,
        { headers, cache: "no-store" }
      ).catch(() => null),
      fetch(
        `${supabaseUrl}/rest/v1/accounts_snapshot?select=*&order=ts.desc&limit=1`,
        { headers, cache: "no-store" }
      ).catch(() => null),
      fetch(
        `${supabaseUrl}/rest/v1/settings?select=value,updated_at&key=eq.live_market_data&limit=1`,
        { headers, cache: "no-store" }
      ).catch(() => null),
    ]);

    let heartbeat = null;
    if (hbRes?.ok) {
      const list = await hbRes.json();
      if (Array.isArray(list) && list.length > 0) heartbeat = list[0];
    }

    let snapshot = null;
    if (snapRes?.ok) {
      const list = await snapRes.json();
      if (Array.isArray(list) && list.length > 0) snapshot = list[0];
    }

    let liveOpenPositions: Record<string, unknown>[] = [];
    if (marketRes?.ok) {
      try {
        const mList = await marketRes.json();
        if (Array.isArray(mList) && mList.length > 0 && mList[0]?.value?.open_positions) {
          liveOpenPositions = mList[0].value.open_positions;
        }
      } catch {
        // ignore
      }
    }

    const liveFloatingPnl = liveOpenPositions.reduce(
      (sum, p) => sum + Number(p.profit || 0),
      0
    );
    const liveOpenCount = liveOpenPositions.length;

    // Synthesise or enrich snapshot with real-time heartbeat & live_market_data
    // so equity, balance, floating P/L, and open positions count are NEVER delayed by 12s!
    if (!snapshot && heartbeat) {
      snapshot = {
        ts:                   heartbeat.ts,
        equity:               heartbeat.equity,
        balance:              heartbeat.balance,
        open_positions_count: liveOpenCount,
        open_positions:       liveOpenCount,
        daily_pnl:            Number(liveFloatingPnl.toFixed(2)),
        drawdown_pct:         0,
        execution_mode:       heartbeat.execution_mode,
      };
    } else if (snapshot && heartbeat) {
      snapshot = {
        ...snapshot,
        ts:                   heartbeat.ts,
        equity:               heartbeat.equity ?? snapshot.equity,
        balance:              heartbeat.balance ?? snapshot.balance,
        open_positions_count: liveOpenCount,
        open_positions:       liveOpenCount,
        daily_pnl:            liveOpenCount > 0
          ? Number(liveFloatingPnl.toFixed(2))
          : Number(((heartbeat.equity ?? snapshot.equity) - (heartbeat.balance ?? snapshot.balance)).toFixed(2)),
      };
    }

    // Determine online status
    let isOnline = false;
    if (heartbeat?.ts) {
      const ageMs = Date.now() - new Date(heartbeat.ts).getTime();
      isOnline = heartbeat.mt5_connected === true && ageMs < 45_000;
    }

    return NextResponse.json(
      {
        success: true,
        is_online: isOnline,
        heartbeat,
        snapshot,
        open_positions: liveOpenPositions,
        timestamp: new Date().toISOString(),
      },
      { headers: { "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0" } }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Telemetry error" },
      { status: 500 }
    );
  }
}
