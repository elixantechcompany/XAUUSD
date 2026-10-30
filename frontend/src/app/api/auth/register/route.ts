import { NextResponse, type NextRequest } from "next/server";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

export async function POST(request: NextRequest) {
  try {
    const { email, password, full_name } = await request.json();

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required" },
        { status: 400 }
      );
    }

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || DEFAULT_SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || DEFAULT_SUPABASE_SERVICE_KEY;

    // 1. Try creating the user with email_confirm = true directly via Admin API
    const createUrl = `${supabaseUrl}/auth/v1/admin/users`;
    const createRes = await fetch(createUrl, {
      method: "POST",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
        email_confirm: true,
        user_metadata: {
          full_name: full_name?.trim() || "",
          email_verified: true,
        },
      }),
    });

    const createData = await createRes.json();

    // If successfully created
    if (createRes.ok) {
      return NextResponse.json({
        success: true,
        user: createData,
        message: "User registered and email auto-confirmed",
      });
    }

    // 2. If user already exists, update their password & confirm their email
    if (
      createData.message?.toLowerCase().includes("already registered") ||
      createRes.status === 422
    ) {
      // Find the existing user ID
      const listUrl = `${supabaseUrl}/auth/v1/admin/users?page=1&per_page=50`;
      const listRes = await fetch(listUrl, {
        headers: {
          apikey: serviceKey,
          Authorization: `Bearer ${serviceKey}`,
        },
      });

      if (listRes.ok) {
        const listData = await listRes.json();
        const existing = listData.users?.find(
          (u: { email?: string }) =>
            u.email?.toLowerCase() === email.trim().toLowerCase()
        );

        if (existing) {
          // Update password and confirm email
          const updateUrl = `${supabaseUrl}/auth/v1/admin/users/${existing.id}`;
          const updateRes = await fetch(updateUrl, {
            method: "PUT",
            headers: {
              apikey: serviceKey,
              Authorization: `Bearer ${serviceKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              password,
              email_confirm: true,
              user_metadata: {
                full_name: full_name?.trim() || existing.user_metadata?.full_name || "",
                email_verified: true,
              },
            }),
          });

          if (updateRes.ok) {
            return NextResponse.json({
              success: true,
              message: "Existing user account updated and email confirmed",
            });
          }
        }
      }
    }

    return NextResponse.json(
      { error: createData.message || "Failed to register user" },
      { status: createRes.status || 500 }
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
