/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0B0B0B",
        surface: "#111111",
        border: "#1E1E1E",
      },
    },
  },
  plugins: [],
};
