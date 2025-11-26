/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jre: {
          dark: '#1a1a1a',
          darker: '#0d0d0d',
          accent: '#dc2626',
          gold: '#d4a843',
        },
      },
    },
  },
  plugins: [],
}
