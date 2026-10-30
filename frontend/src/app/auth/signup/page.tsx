"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import {
  Zap,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowLeft,
  User,
  Mail,
  Lock,
  ShieldCheck,
  Activity,
  Check,
} from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName]         = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const pwLengthOk = password.length >= 8;
  const pwHasNumber = /\d/.test(password);
  const pwHasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  const pwStrong = pwLengthOk && (pwHasNumber || pwHasSpecial);
  const pwMatch  = password === confirm && confirm.length > 0;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!pwLengthOk) return setError("Password must be at least 8 characters.");
    if (!pwMatch)    return setError("Passwords do not match.");

    setLoading(true);
    setError(null);
    try {
      // 1. Call auto-confirm registration API endpoint
      const regRes = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          full_name: name.trim(),
        }),
      });

      const regData = await regRes.json();
      if (!regRes.ok) {
        throw new Error(regData.error || "Failed to create account.");
      }

      // 2. Automatically log in the user immediately
      const { error: signInError } = await getSupabaseClient().auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (signInError) {
        // Fallback: route them to login with a pre-filled state
        router.replace(`/auth/login?email=${encodeURIComponent(email)}&verified=1`);
      } else {
        // Direct entry to Trading Desk Overview
        router.replace("/overview");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#070A0F] text-[#F2F5F9] flex flex-col justify-between relative overflow-hidden px-4 py-8">
      {/* ── Background Ambient Glow Effects ── */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[450px] bg-gradient-to-b from-blue-600/15 via-gold/10 to-transparent blur-[130px] pointer-events-none -z-10" />
      <div className="absolute bottom-0 right-10 w-[400px] h-[400px] bg-emerald-500/10 blur-[140px] pointer-events-none -z-10" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1b253512_1px,transparent_1px),linear-gradient(to_bottom,#1b253512_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] pointer-events-none -z-10" />

      {/* Top Header Navigation */}
      <div className="w-full max-w-5xl mx-auto flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-text-secondary hover:text-white transition-colors bg-[#121821]/60 hover:bg-[#1A2230] border border-[#243043]/80 px-3.5 py-1.5 rounded-inner"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Home
        </Link>

        <div className="flex items-center gap-2 text-[11px] font-mono text-gold bg-gold/10 border border-gold/30 px-3 py-1 rounded-full">
          <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
          INSTANT ACCESS DESK
        </div>
      </div>

      {/* Main Sign Up Card */}
      <div className="w-full max-w-lg mx-auto my-auto">
        <div className="bg-[#0D131C]/90 backdrop-blur-xl border border-[#243043] rounded-card p-8 sm:p-10 shadow-[0_0_50px_rgba(0,0,0,0.6)] relative overflow-hidden">
          {/* Gold top edge accent */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-gold/60 to-transparent" />

          {/* Logo & Headline */}
          <div className="text-center mb-7">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 rounded-xl mb-3 shadow-[0_0_20px_rgba(212,175,55,0.2)]">
              <Zap className="w-6 h-6 text-gold fill-gold/20" />
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Create Your Trading Account
            </h1>
            <p className="text-text-secondary text-xs sm:text-sm mt-1">
              Instant activation · No confirmation email waiting · Direct MT5 access
            </p>
          </div>

          {/* Sign Up Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {error && (
              <div className="flex items-start gap-2.5 bg-red-950/40 border border-red-800/50 rounded-inner p-3 text-xs text-red-300 animate-shake">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-loss" aria-hidden />
                <span>{error}</span>
              </div>
            )}

            {/* Full Name */}
            <div className="space-y-1.5">
              <label htmlFor="name" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  autoComplete="name"
                  placeholder="Hannington"
                  className="w-full bg-[#121821] border border-[#243043] rounded-inner pl-10 pr-4 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30 transition-all font-sans"
                />
              </div>
            </div>

            {/* Email Field */}
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  className="w-full bg-[#121821] border border-[#243043] rounded-inner pl-10 pr-4 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30 transition-all font-sans"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password"
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  className="w-full bg-[#121821] border border-[#243043] rounded-inner pl-10 pr-11 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30 transition-all font-sans"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors p-1"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {/* Password strength tags */}
              {password && (
                <div className="flex items-center gap-2 pt-1">
                  <div className="h-1 flex-1 bg-[#1A2230] rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        pwStrong ? "w-full bg-emerald-500" : pwLengthOk ? "w-2/3 bg-amber-400" : "w-1/3 bg-red-500"
                      }`}
                    />
                  </div>
                  <span className={`text-[11px] font-mono ${pwStrong ? "text-emerald-400" : pwLengthOk ? "text-amber-400" : "text-red-400"}`}>
                    {pwStrong ? "Strong" : pwLengthOk ? "Medium" : "Too short"}
                  </span>
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-1.5">
              <label htmlFor="confirm" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="confirm"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="Repeat your password"
                  className="w-full bg-[#121821] border border-[#243043] rounded-inner pl-10 pr-11 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30 transition-all font-sans"
                />
                {confirm && (
                  <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
                    {pwMatch ? (
                      <Check className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-400" />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !name || !pwLengthOk || !pwMatch}
              className="w-full mt-2 bg-gradient-to-r from-gold via-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 disabled:opacity-50 text-black font-extrabold py-3.5 rounded-inner text-sm shadow-[0_0_25px_rgba(212,175,55,0.25)] transition-all active:scale-[0.98] min-h-[46px] flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin text-black" />
                  <span>Activating Account...</span>
                </>
              ) : (
                "Create Account & Launch Desk"
              )}
            </button>
          </form>

          {/* Sign in link */}
          <div className="mt-6 pt-6 border-t border-[#1B2535] text-center text-xs text-text-secondary">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-gold font-bold hover:underline ml-1">
              Sign In
            </Link>
          </div>
        </div>

        {/* Security Disclaimers */}
        <div className="mt-6 flex items-center justify-center gap-3 text-center text-[11px] text-text-secondary/70">
          <ShieldCheck className="w-3.5 h-3.5 text-gold shrink-0" />
          <span>Local machine execution · Bank-grade Supabase session authentication</span>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="text-center text-[11px] text-text-secondary/60">
        &copy; {new Date().getFullYear()} Elixan Quant Systems · Autonomous SMC Trading Desk
      </div>
    </div>
  );
}
