"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Zap, Eye, EyeOff, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { error: authError } = await getSupabaseClient()
        .auth.signInWithPassword({ email, password });
      if (authError) throw authError;
      router.replace("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign in failed. Check your email and password.");
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
            Welcome back
          </h1>
          <p className="text-text-secondary text-sm mt-1">
            Sign in to your trading dashboard
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {error && (
            <div className="flex items-start gap-2 bg-loss/10 border border-loss/20 rounded-inner p-3 text-sm text-loss">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="email" className="text-sm font-medium text-text-primary">
              Email
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

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-sm font-medium text-text-primary">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 pr-11 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw
                  ? <EyeOff className="w-4 h-4" aria-hidden />
                  : <Eye className="w-4 h-4" aria-hidden />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Link
              href="/auth/forgot-password"
              className="text-xs text-accent hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full bg-accent hover:bg-blue-600 disabled:opacity-50 text-white font-semibold py-3 rounded-inner text-sm transition-colors min-h-[44px]"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {/* Sign up link */}
        <p className="text-center text-sm text-text-secondary">
          New here?{" "}
          <Link href="/auth/signup" className="text-accent font-medium hover:underline">
            Create an account
          </Link>
        </p>

        {/* Safety note */}
        <p className="text-center text-xs text-text-secondary/60">
          Your MT5 credentials are never stored here. This dashboard uses Supabase authentication only.
        </p>
      </div>
    </div>
  );
}
