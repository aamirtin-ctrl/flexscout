import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0c10',
        surface: '#141720',
        border: '#1e2433',
        primary: '#3b82f6',
        amber: '#f59e0b',
        green: '#10b981',
        red: '#ef4444',
        muted: '#64748b',
      },
      fontFamily: {
        mono: ['Geist Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
