import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json({ error: "Email is required" }, { status: 400 });
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    // Search for user in admin list
    const listUrl = `${supabaseUrl}/auth/v1/admin/users?page=1&per_page=100`;
    const listRes = await fetch(listUrl, {
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
      },
    });

    if (!listRes.ok) {
      return NextResponse.json(
        { error: "Failed to query authentication service" },
        { status: 500 }
      );
    }

    const listData = await listRes.json();
    const user = listData.users?.find(
      (u: { email?: string }) => u.email?.toLowerCase() === email.trim().toLowerCase()
    );

    if (!user) {
      return NextResponse.json(
        { error: `No registered account found for ${email}` },
        { status: 404 }
      );
    }

    // Update user to confirmed
    const updateUrl = `${supabaseUrl}/auth/v1/admin/users/${user.id}`;
    const updateRes = await fetch(updateUrl, {
      method: "PUT",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email_confirm: true,
        user_metadata: {
          ...user.user_metadata,
          email_verified: true,
        },
      }),
    });

    if (!updateRes.ok) {
      const updateData = await updateRes.json();
      return NextResponse.json(
        { error: updateData.message || "Failed to confirm email" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: `Account ${email} has been verified successfully. You can now sign in.`,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
