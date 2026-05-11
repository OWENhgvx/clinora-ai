/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        clinora: {
          blue: "#2563EB",
          blueHover: "#1D4ED8",
          deepBlue: "#0F3D73",
          teal: "#14B8A6",
          lightTeal: "#CCFBF1",
          background: "#F8FAFC",
          card: "#FFFFFF",
          textPrimary: "#0F172A",
          textSecondary: "#475569",
          border: "#E2E8F0",
        },
      },
    },
  },
  plugins: [],
};
