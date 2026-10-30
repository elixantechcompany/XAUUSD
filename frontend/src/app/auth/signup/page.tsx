"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Zap, Eye, EyeOff, AlertCircle, CheckCircle2 } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [done, setDone]         = useState(false);

  const pwStrong = password.length >= 8;
  const pwMatch  = password === confirm && confirm.length > 0;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!pwStrong)       return setError("Password must be at least 8 characters.");
    if (!pwMatch)        return setError("Passwords do not match.");

    setLoading(true);
    setError(null);
    try {
      const { error: authError } = await getSupabaseClient().auth.signUp({
        email,
        password,
        options: { data: { full_name: name.trim() } },
      });
      if (authError) throw authError;
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-profit/10 border border-profit/20 rounded-xl mb-2">
            <CheckCircle2 className="w-6 h-6 text-profit" />
          </div>
          <h1 className="text-xl font-bold text-text-primary">Check your email</h1>
          <p className="text-text-secondary text-sm">
            We sent a confirmation link to <strong className="text-text-primary">{email}</strong>.
            Click it to activate your account, then sign in.
          </p>
          <Link
            href="/auth/login"
            className="inline-block w-full bg-accent text-white font-semibold py-3 rounded-inner text-sm text-center hover:bg-blue-600 transition-colors"
          >
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm space-y-8">

        {/* Logo */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-accent/10 border border-accent/20 rounded-xl mb-4">
            <Zap className="w-6 h-6 text-accent" aria-hidden />
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Create account</h1>
          <p className="text-text-secondary text-sm mt-1">
            Your personal trading bot dashboard
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
            <label htmlFor="name" className="text-sm font-medium text-text-primary">Full name</label>
            <input
              id="name" type="text" value={name}
              onChange={(e) => setName(e.target.value)}
              required autoComplete="name" placeholder="Hannington"
              className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="email" className="text-sm font-medium text-text-primary">Email</label>
            <input
              id="email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              required autoComplete="email" placeholder="you@example.com"
              className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-sm font-medium text-text-primary">Password</label>
            <div className="relative">
              <input
                id="password" type={showPw ? "text" : "password"} value={password}
                onChange={(e) => setPassword(e.target.value)}
                required autoComplete="new-password" placeholder="••••••••"
                className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 pr-11 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
              />
              <button type="button" onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                aria-label={showPw ? "Hide" : "Show"}>
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {password && (
              <p className={`text-xs ${pwStrong ? "text-profit" : "text-warning"}`}>
                {pwStrong ? "✓ Strong enough" : "At least 8 characters required"}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="confirm" className="text-sm font-medium text-text-primary">Confirm password</label>
            <input
              id="confirm" type="password" value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required autoComplete="new-password" placeholder="••••••••"
              className="w-full bg-surface-2 border border-border rounded-inner px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent transition-colors"
            />
            {confirm && (
              <p className={`text-xs ${pwMatch ? "text-profit" : "text-loss"}`}>
                {pwMatch ? "✓ Passwords match" : "Passwords do not match"}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !email || !name || !pwStrong || !pwMatch}
            className="w-full bg-accent hover:bg-blue-600 disabled:opacity-50 text-white font-semibold py-3 rounded-inner text-sm transition-colors min-h-[44px]"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-text-secondary">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-accent font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
