/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Tahoe macOS colors
        tahoe: {
          bg: '#0B0B0C',
          panel: 'rgba(22, 22, 24, 0.8)',
          border: 'rgba(255, 255, 255, 0.12)',
          accent: '#0A84FF',
          text: '#F5F5F7',
          textMuted: '#98989D',
        },
      },
      backdropBlur: {
        'tahoe': '20px',
      },
      borderRadius: {
        'tahoe': '18px',
        'tahoe-sm': '12px',
      },
      gridTemplateColumns: {
        '20': 'repeat(20, minmax(0, 1fr))',
      },
    },
  },
  plugins: [],
}
