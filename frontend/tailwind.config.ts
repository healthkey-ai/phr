import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * HealthKey Tailwind config — mirrors healthkey/ui.v2/tailwind.config.ts.
 *
 * Two color systems live here:
 *  1. shadcn semantic tokens (background/foreground/card/muted/...) — used by shadcn primitives
 *  2. healthkey.* namespace + brand/success/warning/error scales — used directly in app code
 *
 * All values come from CSS custom properties defined in src/index.css.
 */
const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: ["Manrope", "-apple-system", "Roboto", "Helvetica", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        display: ["48px", { lineHeight: "56px", fontWeight: "800" }],
        h1: ["32px", { lineHeight: "40px", fontWeight: "700" }],
        h2: ["24px", { lineHeight: "32px", fontWeight: "700" }],
        h3: ["20px", { lineHeight: "28px", fontWeight: "600" }],
        h4: ["18px", { lineHeight: "24px", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "500" }],
        body: ["14px", { lineHeight: "20px", fontWeight: "500" }],
        "body-sm": ["13px", { lineHeight: "18px", fontWeight: "500" }],
        caption: ["12px", { lineHeight: "16px", fontWeight: "500" }],
      },
      colors: {
        // shadcn semantic tokens
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },

        // HealthKey Design System namespace
        healthkey: {
          // Background Colors
          "bg-primary": "hsl(var(--app-bg-primary))",
          "bg-secondary": "hsl(var(--app-bg-secondary))",
          "bg-active": "hsl(var(--app-bg-active))",

          // Text Colors
          "text-primary": "hsl(var(--text-primary-900))",
          "text-secondary": "hsl(var(--text-secondary-700))",
          "text-tertiary": "hsl(var(--text-quaternary-500))",
          "text-quaternary": "hsl(var(--text-quaternary-500))",
          "text-disabled": "hsl(var(--text-disabled))",
          "text-brand": "hsl(var(--text-brand-secondary-700))",
          "text-white": "hsl(var(--text-white))",

          // Border Colors
          "border-secondary": "hsl(var(--border-secondary))",

          // Gray Scale
          "gray-50": "hsl(var(--gray-50))",
          "gray-100": "hsl(var(--gray-100))",
          "gray-200": "hsl(var(--gray-200))",
          "gray-700": "hsl(var(--gray-700))",

          // Brand Colors
          "brand-25": "hsl(var(--brand-25))",
          "brand-50": "hsl(var(--brand-50))",
          "brand-200": "hsl(var(--brand-200))",
          "brand-700": "hsl(var(--brand-700))",
          "brand-alt": "hsl(var(--brand-primary-alt))",
          "brand-green": "hsl(var(--brand-green-500))",

          // Link Colors
          "link-primary": "hsl(var(--link-primary))",
          "link-hover": "hsl(var(--link-primary-hover))",
        },

        // Direct brand scale (matches healthkey exactly: 25/50/200/700/alt)
        brand: {
          25: "hsl(var(--brand-25))",
          50: "hsl(var(--brand-50))",
          200: "hsl(var(--brand-200))",
          700: "hsl(var(--brand-700))",
          alt: "hsl(var(--brand-primary-alt))",
          green: "hsl(var(--brand-green-500))",
        },

        // Status scales (matches healthkey: 50/200/700)
        success: {
          50: "hsl(var(--success-50))",
          200: "hsl(var(--success-200))",
          700: "hsl(var(--success-700))",
        },
        warning: {
          50: "hsl(var(--warning-50))",
          200: "hsl(var(--warning-200))",
          700: "hsl(var(--warning-700))",
        },
        error: {
          50: "hsl(var(--error-50))",
          200: "hsl(var(--error-200))",
          700: "hsl(var(--error-700))",
        },
      },
      borderRadius: {
        none: "0",
        sm: "calc(var(--radius) - 4px)",
        DEFAULT: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        lg: "var(--radius)",
        xl: "calc(var(--radius) + 4px)",
        full: "9999px",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(10, 13, 18, 0.05)",
        DEFAULT: "0 4px 6px rgba(10, 13, 18, 0.07)",
        md: "0 4px 6px rgba(10, 13, 18, 0.07)",
        lg: "0 10px 15px rgba(10, 13, 18, 0.1)",
        xl: "0 20px 25px rgba(10, 13, 18, 0.15)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [animate],
};

export default config;
