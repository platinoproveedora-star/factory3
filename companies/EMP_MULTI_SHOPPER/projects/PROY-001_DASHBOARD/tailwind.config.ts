import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0f172a",
        card: "#1e293b",
        border: "#334155",
        muted: "#64748b",
        primary: "#3b82f6",
      },
    },
  },
  plugins: [],
};

export default config;
