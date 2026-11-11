import { NextResponse, type NextRequest } from "next/server";
import { getAdminSupabaseClient } from "@/lib/supabase/server";

/**
 * POST /api/auth/confirm-email
 *
 * Auto-confirms a user's email using the server-side admin client.
 */
export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email || typeof email !== "string") {
      return NextResponse.json({ error: "Email is required" }, { status: 400 });
    }

    const adminClient = getAdminSupabaseClient();

    const { data: users, error: listError } = await adminClient.auth.admin.listUsers();
    if (listError) {
      return NextResponse.json({ error: listError.message }, { status: 500 });
    }

    const user = users.users.find(
      (u) => u.email?.toLowerCase() === email.trim().toLowerCase()
    );

    if (!user) {
      return NextResponse.json({ error: "No account found for that email" }, { status: 404 });
    }

    const { error: updateError } = await adminClient.auth.admin.updateUserById(
      user.id,
      { email_confirm: true }
    );

    if (updateError) {
      return NextResponse.json({ error: updateError.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
