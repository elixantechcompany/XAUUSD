"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import {
  Zap,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  Mail,
  ShieldCheck,
  Activity,
} from "lucide-react";

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
    <div className="min-h-screen bg-[#070A0F] text-[#F2F5F9] flex flex-col justify-between relative overflow-hidden px-4 py-8">
      {/* ── Background Ambient Glow Effects ── */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[450px] bg-gradient-to-b from-blue-600/15 via-gold/10 to-transparent blur-[130px] pointer-events-none -z-10" />
      <div className="absolute bottom-0 right-10 w-[400px] h-[400px] bg-emerald-500/10 blur-[140px] pointer-events-none -z-10" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1b253512_1px,transparent_1px),linear-gradient(to_bottom,#1b253512_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] pointer-events-none -z-10" />

      {/* Top Header Navigation */}
      <div className="w-full max-w-5xl mx-auto flex items-center justify-between">
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 text-xs font-semibold text-text-secondary hover:text-white transition-colors bg-[#121821]/60 hover:bg-[#1A2230] border border-[#243043]/80 px-3.5 py-1.5 rounded-inner"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Sign In
        </Link>

        <div className="flex items-center gap-2 text-[11px] font-mono text-text-secondary bg-[#121821]/80 border border-[#243043] px-3 py-1 rounded-full">
          ACCOUNT RECOVERY
        </div>
      </div>

      {/* Main Reset Card */}
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
              {done ? "Check Your Inbox" : "Reset Password"}
            </h1>
            <p className="text-text-secondary text-xs sm:text-sm mt-1">
              {done
                ? "We dispatched a secure recovery link to your email"
                : "Enter your registered email to receive a recovery link"}
            </p>
          </div>

          {done ? (
            <div className="space-y-5">
              <div className="flex items-start gap-3 bg-emerald-950/40 border border-emerald-800/50 rounded-inner p-4 text-xs text-emerald-300">
                <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-emerald-400" aria-hidden />
                <span className="leading-relaxed">
                  We sent a recovery link to <strong className="text-white">{email}</strong>. The link expires in 1 hour.
                </span>
              </div>
              <Link
                href="/auth/login"
                className="flex items-center justify-center gap-2 w-full bg-[#121821] hover:bg-[#1A2230] border border-[#243043] text-white font-semibold py-3 rounded-inner text-sm transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                Return to Sign In
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {error && (
                <div className="flex items-start gap-2.5 bg-red-950/40 border border-red-800/50 rounded-inner p-3 text-xs text-red-300">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-loss" aria-hidden />
                  <span>{error}</span>
                </div>
              )}

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

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full mt-2 bg-gradient-to-r from-gold via-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 disabled:opacity-50 text-black font-extrabold py-3.5 rounded-inner text-sm shadow-[0_0_25px_rgba(212,175,55,0.25)] transition-all active:scale-[0.98] min-h-[46px] flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin text-black" />
                    <span>Sending Link...</span>
                  </>
                ) : (
                  "Send Recovery Link"
                )}
              </button>

              <div className="pt-2 text-center">
                <Link
                  href="/auth/login"
                  className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>

        {/* Security Disclaimers */}
        <div className="mt-6 flex items-center justify-center gap-3 text-center text-[11px] text-text-secondary/70">
          <ShieldCheck className="w-3.5 h-3.5 text-gold shrink-0" />
          <span>Secure cryptographic token verification via Supabase Auth</span>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="text-center text-[11px] text-text-secondary/60">
        &copy; {new Date().getFullYear()} Elixan Quant Systems · Autonomous SMC Trading Desk
      </div>
    </div>
  );
}
