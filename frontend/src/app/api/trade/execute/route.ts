import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      symbol    = "BTCUSD",
      direction = "SELL",
      volume    = 0.01,
      rr_ratio  = 3.0,
      entry_price, stop_loss, take_profit,
      reason    = "Manual execution via Web Terminal",
    } = body;

    const supabaseUrl = getSupabaseUrl();
    const headers     = getServiceHeaders();

    const cmdPayload = {
      type: "EXECUTE_TRADE",
      payload: {
        symbol:      symbol.toUpperCase(),
        direction:   direction.toUpperCase(),
        volume:      Number(volume) || 0.01,
        rr_ratio:    Number(rr_ratio) || 3.0,
        entry_price: entry_price ? Number(entry_price) : undefined,
        stop_loss:   stop_loss   ? Number(stop_loss)   : undefined,
        take_profit: take_profit ? Number(take_profit) : undefined,
        reason,
        requested_at: new Date().toISOString(),
      },
      status: "pending",
    };

    const cmdRes = await fetch(`${supabaseUrl}/rest/v1/commands`, {
      method: "POST", headers, body: JSON.stringify(cmdPayload),
    });

    if (!cmdRes.ok) {
      const err = await cmdRes.text();
      return NextResponse.json({ error: `Command dispatch failed: ${err}` }, { status: 500 });
    }

    // Optimistically record signal
    const sigId = `sig_${symbol.toLowerCase()}_${Date.now()}`;
    const now   = new Date().toISOString();
    await fetch(`${supabaseUrl}/rest/v1/signals`, {
      method: "POST",
      headers: { ...headers, Prefer: "resolution=merge-duplicates" },
      body: JSON.stringify({
        id: sigId, created_at: now, updated_at: now,
        instrument: symbol.toUpperCase(), timeframe: "H1",
        direction: direction.toUpperCase() === "BUY" ? "BULLISH" : "BEARISH",
        state: "ORDER_PENDING", status: "new",
        entry:             entry_price ? Number(entry_price) : null,
        stop_loss:         stop_loss   ? Number(stop_loss)   : null,
        take_profit:       take_profit ? Number(take_profit) : null,
        suggested_lot_size: Number(volume) || 0.01,
        rr_ratio: Number(rr_ratio) || 3.0,
        strategy_version: "1.2",
      }),
    }).catch(() => null);

    return NextResponse.json({
      success: true,
      message: `Order dispatched: ${symbol} ${direction}`,
      command: cmdPayload,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Trade execution error" },
      { status: 500 }
    );
  }
}
