/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"DM Mono"', 'monospace'],
        display: ['"Bebas Neue"', 'sans-serif'],
        sans: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        bg: '#080a0f',
        surface: '#111620',
        border: '#1e2530',
        accent: '#00e5ff',
        accent2: '#7c3aed',
        muted: '#64748b',
      },
    },
  },
  plugins: [],
}
