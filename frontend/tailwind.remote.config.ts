import type { Config } from "tailwindcss";
import baseConfig from "./tailwind.config";

const config: Config = {
  ...baseConfig,
  prefix: "",
  important: ".hk-labs-root",
  content: [
    "./src/federation/**/*.{ts,tsx}",
    "./src/components/labs/**/*.{ts,tsx}",
    "./src/components/ui/**/*.{ts,tsx}",
    "./src/components/healthkey/**/*.{ts,tsx}",
  ],
};

export default config;
