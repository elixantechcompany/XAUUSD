import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "100";
    const instrument = searchParams.get("instrument");

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
    };

    let url = `${supabaseUrl}/rest/v1/trades?select=*&order=open_time.desc&limit=${limit}`;
    if (instrument) {
      url += `&instrument=eq.${encodeURIComponent(instrument.toUpperCase())}`;
    }

    const res = await fetch(url, { headers, cache: "no-store" });
    if (!res.ok) {
      return NextResponse.json({ trades: [] });
    }

    const trades = await res.json();
    return NextResponse.json(
      {
        success: true,
        trades: trades || [],
      },
      {
        headers: {
          "Cache-Control": "public, s-maxage=1, stale-while-revalidate=2",
        },
      }
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Error listing trades";
    return NextResponse.json({ error: msg, trades: [] }, { status: 500 });
  }
}
