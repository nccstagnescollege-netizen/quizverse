import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
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
        },
        cyber: {
          cyan: '#00f5d4',
          purple: '#9d4edd',
          pink: '#f72585',
          gold: '#ffd166',
        },
        surface: {
          base: 'var(--surface-base)',
          elevated: 'var(--surface-elevated)',
          panel: 'var(--surface-panel)',
          card: 'var(--surface-card)',
          border: 'var(--surface-border)',
        },
        app: {
          bg: 'var(--background)',
          fg: 'var(--foreground)',
          card: 'var(--surface-card)',
          border: 'var(--surface-border)',
          primary: 'var(--brand-primary)',
          accent: 'var(--brand-accent)',
          success: 'var(--status-success)',
          warning: 'var(--status-warning)',
          error: 'var(--status-error)',
          info: 'var(--status-info)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.25)',
        'glass-md': '0 8px 32px 0 rgba(0, 0, 0, 0.35)',
        'glass-lg': '0 16px 48px 0 rgba(0, 0, 0, 0.5)',
        'glow-cyan': '0 0 24px -4px rgba(0, 245, 212, 0.45)',
        'glow-primary': '0 0 24px -4px rgba(70, 104, 250, 0.45)',
        'glow-purple': '0 0 24px -4px rgba(157, 78, 221, 0.45)',
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
          '50%': { transform: 'translateY(-8px)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
