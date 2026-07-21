import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16201f",
        paper: "#f7f8f4",
        moss: "#506f5b",
        steel: "#3e6c8d",
        clay: "#a85f3e",
        line: "#d9ded5"
      }
    }
  },
  plugins: []
};

export default config;
