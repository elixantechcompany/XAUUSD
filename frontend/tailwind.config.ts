import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Design system tokens from Developer Guide §6
        background:   "#0B0F14",
        surface:      "#121821",
        "surface-2":  "#1A2230",
        border:       "#243043",
        "text-primary":   "#F2F5F9",
        "text-secondary": "#8A97A8",
        accent:   "#3B82F6",
        profit:   "#22C55E",
        loss:     "#EF4444",
        warning:  "#F59E0B",
        gold:     "#D4AF37",
      },
      fontFamily: {
        sans: ["Inter", "Geist", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card:  "16px",
        inner: "12px",
        DEFAULT: "8px",
      },
      spacing: {
        // 8px grid
        "0.5": "4px",
        "1":   "8px",
        "2":   "16px",
        "3":   "24px",
        "4":   "32px",
        "5":   "40px",
        "6":   "48px",
      },
    },
  },
  plugins: [],
};

export default config;
