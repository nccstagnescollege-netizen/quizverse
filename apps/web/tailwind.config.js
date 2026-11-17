/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f5ff',
          100: '#e0ebff',
          200: '#c7d9fe',
          300: '#a3beff',
          400: '#7599ff',
          500: '#4668fa',
          600: '#2b44ef',
          700: '#2032d6',
          800: '#1e2cb0',
          900: '#1b278e',
          950: '#0d1354',
        },
        cyber: {
          cyan: '#00f5d4',
          neon: '#7b2cbf',
          purple: '#9d4edd',
          pink: '#f72585',
          gold: '#ffd166',
        },
        surface: {
          base: '#080a10',
          elevated: '#0f1422',
          panel: '#151c30',
          card: 'rgba(21, 28, 48, 0.65)',
          border: 'rgba(255, 255, 255, 0.08)',
          'border-highlight': 'rgba(123, 44, 191, 0.4)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.35)',
        'glass-md': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glass-lg': '0 16px 48px 0 rgba(0, 0, 0, 0.6)',
        'glow-primary': '0 0 24px -4px rgba(70, 104, 250, 0.5)',
        'glow-cyan': '0 0 24px -4px rgba(0, 245, 212, 0.5)',
        'glow-purple': '0 0 24px -4px rgba(157, 78, 221, 0.5)',
      },
      backdropBlur: {
        glass: '16px',
        heavy: '24px',
      },
      animation: {
        'pulse-glow': 'pulse-glow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        float: 'float 6s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
};
