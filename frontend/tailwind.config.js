/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0E14",
        panel: "#111823",
        panelraised: "#161F2C",
        line: "#243040",
        line2: "#324055",
        cyan: {
          DEFAULT: "#4CD9E0",
          dim: "#2A6E73",
        },
        amber: {
          DEFAULT: "#F2B441",
          dim: "#7A5C22",
        },
        coral: {
          DEFAULT: "#F2665E",
          dim: "#7A342F",
        },
        mint: {
          DEFAULT: "#7BD88F",
          dim: "#3D6D47",
        },
        ink: {
          hi: "#EAF2F5",
          mid: "#9FB1BE",
          lo: "#5C6E7C",
        },
      },
      fontFamily: {
        mono: ["'IBM Plex Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["'Inter'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        board: "0 0 0 1px rgba(76,217,224,0.08), 0 8px 24px -8px rgba(0,0,0,0.6)",
      },
      keyframes: {
        flapin: {
          "0%": { transform: "translateY(-6px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        flapin: "flapin 220ms ease-out",
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
