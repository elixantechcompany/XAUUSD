import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "BotControl", template: "%s | BotControl" },
  description: "XAUUSD / BTCUSD MT5 trading bot dashboard — paper & demo mode",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "BotControl" },
  icons: { icon: "/favicon.ico", apple: "/icons/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0B0F14",
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
      <body className="bg-background text-text-primary antialiased">
        {children}
      </body>
    </html>
  );
}
