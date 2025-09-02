import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0F1117',
        panel: '#151922',
        card: '#1B2130',
        border: '#232B3A',
        'text-primary': '#E8ECF3',
        'text-secondary': '#A2AEC3',
        'text-muted': '#7B869C',
        cyan: '#2DD4FF',
        magenta: '#FF4D8D',
        lime: '#C7F23A',
        yellow: '#FFD84D',
      },
      borderRadius: {
        card: '12px',
        modal: '16px',
      },
      boxShadow: {
        soft: '0 4px 24px rgba(0,0,0,0.35)'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Monaco', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
} satisfies Config

