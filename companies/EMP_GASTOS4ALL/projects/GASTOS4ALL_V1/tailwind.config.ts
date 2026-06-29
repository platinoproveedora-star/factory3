import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#0f172a",
        card:    "#1e293b",
        border:  "#334155",
        muted:   "#64748b",
        primary: "#3b82f6",
      },
    },
  },
  plugins: [],
};

export default config;
