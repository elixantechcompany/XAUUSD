import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      symbol = "BTCUSD",
      direction = "SELL",
      volume = 0.01,
      rr_ratio = 3.0,
      entry_price,
      stop_loss,
      take_profit,
      reason = "Manual 1-Click Execution via Web Terminal",
    } = body;

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    // 1. Dispatch EXECUTE_TRADE command to Supabase
    const cmdPayload = {
      type: "EXECUTE_TRADE",
      payload: {
        symbol: symbol.toUpperCase(),
        direction: direction.toUpperCase(),
        volume: Number(volume) || 0.01,
        rr_ratio: Number(rr_ratio) || 3.0,
        entry_price: entry_price ? Number(entry_price) : undefined,
        stop_loss: stop_loss ? Number(stop_loss) : undefined,
        take_profit: take_profit ? Number(take_profit) : undefined,
        reason,
        requested_at: new Date().toISOString(),
      },
      status: "pending",
    };

    const cmdRes = await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST",
      headers,
      body: JSON.stringify(cmdPayload),
    });

    if (!cmdRes.ok) {
      const err = await cmdRes.text();
      return NextResponse.json({ error: `Command dispatch failed: ${err}` }, { status: 500 });
    }

    // 2. Also record optimistic signal in signals table
    const sigId = `sig_${symbol.toLowerCase()}_${Date.now()}`;
    const now = new Date().toISOString();
    await fetch(`${supabaseUrl}/rest/v1/signals`, {
      method: "POST",
      headers: { ...headers, Prefer: "resolution=merge-duplicates" },
      body: JSON.stringify({
        id: sigId,
        created_at: now,
        updated_at: now,
        instrument: symbol.toUpperCase(),
        timeframe: "H1",
        direction: direction.toUpperCase() === "BUY" ? "BULLISH" : "BEARISH",
        state: "ORDER_PENDING",
        status: "new",
        entry: entry_price ? Number(entry_price) : null,
        stop_loss: stop_loss ? Number(stop_loss) : null,
        take_profit: take_profit ? Number(take_profit) : null,
        suggested_lot_size: Number(volume) || 0.01,
        rr_ratio: Number(rr_ratio) || 3.0,
        strategy_version: "1.0",
      }),
    }).catch(() => null);

    return NextResponse.json({
      success: true,
      message: `Order dispatched to Exness MT5 bridge for ${symbol} ${direction} (0.01 lot, 1:3 RR)`,
      command: cmdPayload,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Trade execution error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
