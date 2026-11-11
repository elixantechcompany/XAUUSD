import { NextResponse } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

/**
 * GET /api/telemetry/heartbeat
 *
 * Server-side route that fetches heartbeat + account snapshot from Supabase
 * using the server-side service headers.
 */
export async function GET() {
  try {
    const supabaseUrl = getSupabaseUrl();
    const headers = getServiceHeaders();

    // Fetch heartbeat and snapshot concurrently
    const [hbRes, snapRes] = await Promise.all([
      fetch(
        `${supabaseUrl}/rest/v1/heartbeats?select=*&order=ts.desc&limit=1`,
        { headers, cache: "no-store" }
      ).catch(() => null),
      fetch(
        `${supabaseUrl}/rest/v1/accounts_snapshot?select=*&order=ts.desc&limit=1`,
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

    // Synthesise a minimal snapshot from heartbeat if DB snapshot not available
    if (!snapshot && heartbeat) {
      snapshot = {
        ts:                  heartbeat.ts,
        equity:              heartbeat.equity,
        balance:             heartbeat.balance,
        open_positions_count: 0,
        open_positions:       0,
        daily_pnl:            0,
        drawdown_pct:         0,
        execution_mode:       heartbeat.execution_mode,
      };
    }

    // Determine online status
    let isOnline = false;
    if (heartbeat?.ts) {
      const ageMs = Date.now() - new Date(heartbeat.ts).getTime();
      isOnline = heartbeat.mt5_connected === true && ageMs < 45_000;
    }

    return NextResponse.json(
      { success: true, is_online: isOnline, heartbeat, snapshot, timestamp: new Date().toISOString() },
      { headers: { "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2" } }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Telemetry error" },
      { status: 500 }
    );
  }
}
