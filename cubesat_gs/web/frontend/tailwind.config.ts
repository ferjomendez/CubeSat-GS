import type { Config } from "tailwindcss";
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "hsl(var(--bg))", raised: "hsl(var(--bg-raised))", line: "hsl(var(--line))",
        fg: "hsl(var(--text))", dim: "hsl(var(--text-dim))",
        nominal: "hsl(var(--nominal))", warn: "hsl(var(--warn))", alarm: "hsl(var(--alarm))", info: "hsl(var(--info))",
        // shadcn tokens
        background: "hsl(var(--bg))", foreground: "hsl(var(--text))", border: "hsl(var(--line))", input: "hsl(var(--line))",
        ring: "hsl(var(--info))", primary: { DEFAULT: "hsl(var(--info))", foreground: "hsl(var(--bg))" },
        secondary: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        destructive: { DEFAULT: "hsl(var(--alarm))", foreground: "hsl(var(--text))" },
        muted: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text-dim))" },
        accent: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        popover: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        card: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
      },
      fontFamily: { label: ["'Barlow Condensed'", "sans-serif"], mono: ["'JetBrains Mono'", "monospace"] },
      borderRadius: { DEFAULT: "2px", sm: "2px", md: "2px", lg: "3px" },
      spacing: { 1: "4px", 2: "8px", 3: "12px", 4: "16px", 5: "20px", 6: "24px", 8: "32px" },
    },
  },
  plugins: [],
} satisfies Config;
