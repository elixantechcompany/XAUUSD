/**
 * Server-side Supabase admin client.
 *
 * Uses the service role key from process.env when available, with safe fallbacks
 * so Vercel serverless routes never crash with 500 if only NEXT_PUBLIC_* vars are set.
 * NEVER import this in client components.
 * Used only in Next.js API routes (app/api/...).
 */
import { createClient } from "@supabase/supabase-js";

const DEFAULT_SUPABASE_URL = "https://bntqfzopbbeosruzjxbw.supabase.co";
const DEFAULT_SUPABASE_SERVICE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ";

let _adminClient: ReturnType<typeof createClient> | null = null;

export function getSupabaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.SUPABASE_URL ||
    DEFAULT_SUPABASE_URL
  );
}

export function getSupabaseServiceKey(): string {
  return (
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    DEFAULT_SUPABASE_SERVICE_KEY
  );
}

export function getAdminSupabaseClient() {
  if (_adminClient) return _adminClient;

  const url = getSupabaseUrl();
  const key = getSupabaseServiceKey();

  _adminClient = createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  return _adminClient;
}

/**
 * Convenience: returns the Supabase URL and service key headers
 * for direct REST API calls.
 */
export function getServiceHeaders(): Record<string, string> {
  const key = getSupabaseServiceKey();

  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  };
}
