import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ELIXAN QUANT — Institutional AI Trading Desk | Gold & Bitcoin",
    template: "%s | ELIXAN QUANT",
  },
  description:
    "Autonomous SMC & Fair Value Gap quantitative trading desk for XAUUSD & BTCUSD with single-terminal multi-account trade copying in <200ms.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "ELIXAN QUANT",
  },
  icons: { icon: "/favicon.ico", apple: "/icons/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#070A0F",
};

/**
 * Root layout — minimal shell.
 *
 * The nav chrome (sidebar / mobile bottom bar / top bar) lives in
 * (app)/layout.tsx so that auth routes (under /auth/*) get a clean
 * full-screen layout without any navigation.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#070A0F] text-[#F2F5F9] antialiased selection:bg-gold/30 selection:text-gold">
        {children}
      </body>
    </html>
  );
}
