import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211d",
        steel: "#315c67",
        moss: "#4f6f52",
        amberline: "#c58b35"
      }
    }
  },
  plugins: []
};

export default config;
