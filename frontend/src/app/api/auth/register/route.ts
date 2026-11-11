import { NextResponse, type NextRequest } from "next/server";
import { getServiceHeaders, getSupabaseUrl } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  try {
    const { email, password, full_name } = await request.json();

    if (!email || !password) {
      return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
    }

    const supabaseUrl = getSupabaseUrl();
    const serviceKey  = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    const headers     = getServiceHeaders();

    // Create user with email_confirm = true (auto-confirm)
    const createRes = await fetch(`${supabaseUrl}/auth/v1/admin/users`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        email:         email.trim().toLowerCase(),
        password,
        email_confirm: true,
        user_metadata: { full_name: full_name?.trim() || "", email_verified: true },
      }),
    });

    const createData = await createRes.json();

    if (createRes.ok) {
      return NextResponse.json({ success: true, user: createData, message: "Registered and email confirmed" });
    }

    // User already exists — update password and confirm
    if (createData.message?.toLowerCase().includes("already registered") || createRes.status === 422) {
      const listRes = await fetch(`${supabaseUrl}/auth/v1/admin/users?page=1&per_page=50`, { headers });
      if (listRes.ok) {
        const listData = await listRes.json();
        const existing = listData.users?.find(
          (u: { email?: string }) => u.email?.toLowerCase() === email.trim().toLowerCase()
        );
        if (existing) {
          const updateRes = await fetch(`${supabaseUrl}/auth/v1/admin/users/${existing.id}`, {
            method: "PUT",
            headers,
            body: JSON.stringify({
              password, email_confirm: true,
              user_metadata: { full_name: full_name?.trim() || existing.user_metadata?.full_name || "" },
            }),
          });
          if (updateRes.ok) {
            return NextResponse.json({ success: true, message: "Account updated and confirmed" });
          }
        }
      }
    }

    return NextResponse.json(
      { error: createData.message || "Failed to register user" },
      { status: createRes.status || 500 }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
