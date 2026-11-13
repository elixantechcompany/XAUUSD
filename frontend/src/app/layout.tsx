import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ELIXAN QUANT — Institutional Quantitative Trading Desk | Spot Gold",
    template: "%s | ELIXAN QUANT",
  },
  description:
    "Autonomous Smart Money Concepts quantitative trading desk for Gold (XAUUSD) with sub-second execution, dynamic break-even, and fast multi-account replication.",
  manifest: "/manifest.json",
  icons: { icon: "/favicon.ico", apple: "/icons/apple-touch-icon.png" },
  other: {
    "mobile-web-app-capable": "yes",
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "black-translucent",
  },
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
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'light') {
                  document.documentElement.classList.remove('dark');
                  document.documentElement.classList.add('light');
                } else {
                  document.documentElement.classList.add('dark');
                  document.documentElement.classList.remove('light');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body className="bg-background text-text-primary antialiased selection:bg-gold/30 selection:text-gold">
        {children}
      </body>
    </html>
  );
}
