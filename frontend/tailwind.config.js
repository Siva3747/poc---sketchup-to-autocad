/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'rgb(10, 10, 12)',
        card: 'rgb(20, 20, 25)',
        primary: {
          50: '#f5f7ff',
          100: '#ebf0ff',
          500: '#3b82f6', // Sleek blue
          600: '#2563eb',
          700: '#1d4ed8',
        },
        accent: {
          emerald: '#10b981', // Green for active modes
          rose: '#f43f5e',    // Rose for deletes
          amber: '#f59e0b',   // Amber for highlights
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'premium': '0 20px 25px -5px rgb(0 0 0 / 0.5), 0 8px 10px -6px rgb(0 0 0 / 0.5)',
      }
    },
  },
  plugins: [],
}
