import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
      typography: {
        invert: {
          css: {
            "--tw-prose-body": "rgb(203 213 225)",
            "--tw-prose-headings": "rgb(241 245 249)",
            "--tw-prose-links": "rgb(96 165 250)",
            "--tw-prose-code": "rgb(226 232 240)",
            "--tw-prose-pre-bg": "rgb(15 23 42)",
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
