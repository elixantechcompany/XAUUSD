"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Zap, AlertCircle, CheckCircle2, ArrowLeft } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail]     = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone]       = useState(false);
  const [error, setError]     = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { error: authError } = await getSupabaseClient().auth.resetPasswordForEmail(
        email,
        { redirectTo: `${window.location.origin}/auth/callback?next=/auth/reset-password` }
      );
      if (authError) throw authError;
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">

        {/* Logo */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-accent/10 border border-accent/20 rounded-xl mb-4">
            <Zap className="w-6 h-6 text-accent" aria-hidden />
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">
            {done ? "Email sent" : "Reset your password"}
          </h1>
          <p className="text-text-secondary text-sm mt-1">
            {done
              ? "Check your inbox for the reset link."
              : "Enter your email and we'll send a reset link."}
          </p>
        </div>

        {done ? (
          <div className="space-y-4">
            <div className="flex items-start gap-3 bg-profit/10 border border-profit/20 rounded-inner p-4 text-sm text-profit">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
              <span>
                We sent a password reset link to <strong>{email}</strong>.
                The link expires in 1 hour.
              </span>
            </div>
            <Link
              href="/auth/login"
              className="flex items-center justify-center gap-2 w-full bg-surface-2 border border-border text-text-primary font-medium py-3 rounded-inner text-sm hover:bg-border transition-colors"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden />
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {error && (
              <div className="flex items-start gap-2 bg-loss/10 border border-loss/20 rounded-inner p-3 text-sm text-loss">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium text-text-primary">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email}
              className="w-full bg-accent hover:bg-blue-600 disabled:opacity-50 text-white font-semibold py-3 rounded-inner text-sm transition-colors min-h-[44px]"
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>

            <Link
              href="/auth/login"
              className="flex items-center justify-center gap-2 w-full text-sm text-text-secondary hover:text-text-primary transition-colors py-2"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden />
              Back to sign in
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
