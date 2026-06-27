/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        base:      'var(--bg-base)',
        surface:   'var(--bg-surface)',
        surface2:  'var(--bg-surface-2)',
        surface3:  'var(--bg-surface-3)',
        accent:    'var(--accent)',
        success:   'var(--success)',
        warning:   'var(--warning)',
        error:     'var(--error)',
        purple:    'var(--purple)',
      },
      borderColor: {
        DEFAULT: 'rgba(255,255,255,0.07)',
      },
      animation: {
        'pulse-dot':  'pulse-dot 1.4s ease-in-out infinite',
        'fade-in':    'fade-in 0.25s ease-out both',
        'spin-slow':  'spin-slow 1.5s linear infinite',
      },
      keyframes: {
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%':      { opacity: '0.4', transform: 'scale(0.85)' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'spin-slow': {
          from: { transform: 'rotate(0deg)' },
          to:   { transform: 'rotate(360deg)' },
        },
      },
    },
  },
  plugins: [],
}
