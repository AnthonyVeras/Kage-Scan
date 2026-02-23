/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: {
        extend: {
            /* ── Ink & Sakura Palette ──────────────────────────── */
            colors: {
                sakura: {
                    50: "#FFF0F3",
                    100: "#FFE0E6",
                    200: "#FFCCD5",
                    300: "#FFB8C6",  /* light */
                    400: "#F391A0",  /* base */
                    500: "#E06B7E",  /* dark */
                    600: "#C94D63",
                    700: "#A83550",
                    800: "#8A2240",
                    900: "#6E1434",
                },
                ink: {
                    50: "#1A1A1A",
                    100: "#171717",
                    200: "#141414",
                    300: "#111111",
                    400: "#0E0E0E",
                    500: "#0C0C0C",
                    600: "#0A0A0A",  /* surface */
                    700: "#070707",
                    800: "#050505",
                    900: "#000000",  /* absolute black */
                },
            },

            /* ── Typography ───────────────────────────────────── */
            fontFamily: {
                sans: ['"Inter"', '"Noto Sans JP"', "system-ui", "sans-serif"],
                display: ['"Outfit"', '"Inter"', "system-ui", "sans-serif"],
                mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
            },

            /* ── Glow Shadows ─────────────────────────────────── */
            boxShadow: {
                "sakura-sm": "0 0 10px rgba(243, 145, 160, 0.15)",
                "sakura-md": "0 0 20px rgba(243, 145, 160, 0.20)",
                "sakura-lg": "0 0 40px rgba(243, 145, 160, 0.25)",
                "sakura-glow": "0 0 60px rgba(255, 184, 198, 0.30), 0 0 120px rgba(243, 145, 160, 0.10)",
                "inner-glow": "inset 0 1px 0 rgba(255, 255, 255, 0.05)",
            },

            /* ── Animations ───────────────────────────────────── */
            keyframes: {
                "fade-in": {
                    "0%": { opacity: "0", transform: "translateY(8px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                "fade-in-scale": {
                    "0%": { opacity: "0", transform: "scale(0.95)" },
                    "100%": { opacity: "1", transform: "scale(1)" },
                },
                "pulse-slow": {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.6" },
                },
                "shimmer": {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
                "glow-pulse": {
                    "0%, 100%": { boxShadow: "0 0 15px rgba(243, 145, 160, 0.15)" },
                    "50%": { boxShadow: "0 0 30px rgba(243, 145, 160, 0.30)" },
                },
            },
            animation: {
                "fade-in": "fade-in 0.4s ease-out both",
                "fade-in-scale": "fade-in-scale 0.3s ease-out both",
                "fade-in-slow": "fade-in 0.8s ease-out both",
                "pulse-slow": "pulse-slow 3s ease-in-out infinite",
                "shimmer": "shimmer 2s linear infinite",
                "glow-pulse": "glow-pulse 2.5s ease-in-out infinite",
            },

            /* ── Spacing & Sizing ─────────────────────────────── */
            backdropBlur: {
                xs: "2px",
            },
            borderRadius: {
                "4xl": "2rem",
            },
        },
    },
    plugins: [],
};
