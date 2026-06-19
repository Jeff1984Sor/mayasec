import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#1E2D6B",
        indigo: "#7C8FFF",
        teal: "#1A8F5E",
        amber: "#F5A623",
        red: "#C94343",
        dark: "#0F1729",
        gray: "#F7F8FC",
      },
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
