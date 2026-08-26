/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Muted blue rather than Picnic's red: the budget states already own
        // green and red, and those must keep meaning exactly one thing.
        brand: {
          50: "#eef6ff",
          100: "#d9ebff",
          500: "#2f6fdb",
          600: "#2559b4",
          700: "#1d478f",
        },
        surface: {
          DEFAULT: "#ffffff",
          muted: "#f6f7f9",
          border: "#e5e7eb",
        },
        positive: { 50: "#ecfdf3", 600: "#0f9d58", 700: "#0b7a44" },
        negative: { 50: "#fef2f2", 600: "#dc2626", 700: "#b91c1c" },
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 24, 40, 0.05), 0 1px 3px rgba(16, 24, 40, 0.06)",
      },
      borderRadius: {
        card: "0.75rem",
      },
    },
  },
  plugins: [],
};
