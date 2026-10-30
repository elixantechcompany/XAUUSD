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
  Lock,
  Mail,
  ShieldCheck,
  Activity,
} from "lucide-react";

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
      router.replace("/overview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign in failed. Check your email and password.");
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

        <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-3 py-1 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          IPC BRIDGE ONLINE
        </div>
      </div>

      {/* Main Sign In Card */}
      <div className="w-full max-w-md mx-auto my-auto">
        <div className="bg-[#0D131C]/90 backdrop-blur-xl border border-[#243043] rounded-card p-8 sm:p-10 shadow-[0_0_50px_rgba(0,0,0,0.6)] relative overflow-hidden">
          {/* Subtle gold top-edge reflection */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-gold/60 to-transparent" />

          {/* Logo & Headline */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br from-gold/20 via-accent/20 to-emerald-500/20 border border-gold/40 rounded-xl mb-3 shadow-[0_0_20px_rgba(212,175,55,0.2)]">
              <Zap className="w-6 h-6 text-gold fill-gold/20" />
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Welcome back
            </h1>
            <p className="text-text-secondary text-xs sm:text-sm mt-1">
              Sign in to your <span className="text-gold font-medium">ELIXAN QUANT</span> trading desk
            </p>
          </div>

          {/* Sign In Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {error && (
              <div className="flex items-start gap-2.5 bg-red-950/40 border border-red-800/50 rounded-inner p-3 text-xs text-red-300 animate-shake">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-loss" aria-hidden />
                <span>{error}</span>
              </div>
            )}

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
                  placeholder="trader@elixanquant.com"
                  className="w-full bg-[#121821] border border-[#243043] rounded-inner pl-10 pr-4 py-3 text-sm text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-gold/60 focus:ring-1 focus:ring-gold/30 transition-all font-sans"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Password
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-xs text-gold hover:text-amber-300 hover:underline transition-colors font-medium"
                >
                  Forgot password?
                </Link>
              </div>
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
                  autoComplete="current-password"
                  placeholder="••••••••••••"
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
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full mt-2 bg-gradient-to-r from-gold via-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 disabled:opacity-50 text-black font-extrabold py-3.5 rounded-inner text-sm shadow-[0_0_25px_rgba(212,175,55,0.25)] transition-all active:scale-[0.98] min-h-[46px] flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin text-black" />
                  <span>Authenticating...</span>
                </>
              ) : (
                "Sign In to Trading Desk"
              )}
            </button>
          </form>

          {/* Sign up prompt */}
          <div className="mt-6 pt-6 border-t border-[#1B2535] text-center text-xs text-text-secondary">
            New to Elixan Quant?{" "}
            <Link href="/auth/signup" className="text-gold font-bold hover:underline ml-1">
              Create an account
            </Link>
          </div>
        </div>

        {/* Security Disclaimers */}
        <div className="mt-6 flex items-center justify-center gap-3 text-center text-[11px] text-text-secondary/70">
          <ShieldCheck className="w-3.5 h-3.5 text-gold shrink-0" />
          <span>MT5 credentials stored exclusively on local laptop · Zero cloud storage</span>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="text-center text-[11px] text-text-secondary/60">
        &copy; {new Date().getFullYear()} Elixan Quant Systems · Autonomous SMC Trading Desk
      </div>
    </div>
  );
}
