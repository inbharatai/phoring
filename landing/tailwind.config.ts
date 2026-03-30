import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#050507',
          elevated: '#0a0a12',
          surface: '#10101a',
        },
        border: {
          DEFAULT: '#1a1a28',
          hover: '#2a2a3e',
          active: '#3a3a52',
        },
        text: {
          primary: '#eaeaef',
          secondary: '#7a7a92',
          tertiary: '#4a4a60',
        },
        accent: {
          blue: '#3d6bff',
          'blue-muted': '#2a4fcc',
          cyan: '#22d3ee',
          amber: '#e5a60a',
          emerald: '#10b981',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      maxWidth: {
        container: '1200px',
      },
      animation: {
        'pulse-slow': 'pulse-slow 4s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 3s ease-in-out infinite',
        'signal': 'signal 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.6' },
        },
        'pulse-ring': {
          '0%, 100%': { opacity: '0.12', transform: 'scale(1)' },
          '50%': { opacity: '0.3', transform: 'scale(1.2)' },
        },
        'signal': {
          '0%, 100%': { opacity: '0.25' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}

export default config
