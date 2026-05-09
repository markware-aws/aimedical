/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,md,mdx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#FFFFFF",
          dark: "#16191C",
        },
        surface: {
          DEFAULT: "#FAFAF7",
          dark: "#1E2125",
        },
        ink: {
          DEFAULT: "#1A1A1A",
          dark: "#E8E8E5",
        },
        muted: {
          DEFAULT: "#5C5C5C",
          dark: "#9CA0A6",
        },
        border: {
          DEFAULT: "#E5E5E0",
          dark: "#2E3338",
        },
        accent: {
          DEFAULT: "#0F4C75",
          dark: "#5BA3D0",
        },
        teal: {
          DEFAULT: "#2A7F7E",
          dark: "#5DB5B3",
        },
        med: {
          DEFAULT: "#3D7B5F",
          dark: "#6FB593",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      maxWidth: {
        prose: "68ch",
        reading: "44rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.04)",
        cardHover: "0 4px 16px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.06)",
      },
      transitionDuration: {
        DEFAULT: "200ms",
      },
    },
  },
  plugins: [],
};
