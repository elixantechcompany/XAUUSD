import { NextResponse } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function GET() {
  try {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    // 1. Fetch latest heartbeat
    const hbRes = await fetch(
      `${supabaseUrl}/rest/v1/heartbeats?select=*&order=ts.desc&limit=1`,
      { headers, cache: "no-store" }
    );
    let heartbeat = null;
    if (hbRes.ok) {
      const hbList = await hbRes.json();
      if (hbList && hbList.length > 0) {
        heartbeat = hbList[0];
      }
    }

    // 2. Fetch latest account snapshot
    const snapRes = await fetch(
      `${supabaseUrl}/rest/v1/accounts_snapshot?select=*&order=ts.desc&limit=1`,
      { headers, cache: "no-store" }
    );
    let snapshot = null;
    if (snapRes.ok) {
      const snapList = await snapRes.json();
      if (snapList && snapList.length > 0) {
        snapshot = snapList[0];
      }
    }

    if (!snapshot && heartbeat) {
      snapshot = {
        ts: heartbeat.ts,
        equity: heartbeat.equity,
        balance: heartbeat.balance,
        margin_free: heartbeat.equity,
        margin_used: 0,
        margin_level: 0,
        open_positions: 0,
        daily_pnl: 0,
        drawdown_pct: 0,
      };
    }

    // 3. Determine if currently online
    let isOnline = false;
    if (heartbeat && heartbeat.ts) {
      const ageMs = Date.now() - new Date(heartbeat.ts).getTime();
      isOnline = heartbeat.mt5_connected && ageMs < 45_000;
    }

    return NextResponse.json({
      success: true,
      is_online: isOnline,
      heartbeat,
      snapshot,
      timestamp: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Telemetry error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
