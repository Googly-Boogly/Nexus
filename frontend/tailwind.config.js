/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#040911',
        card: '#0c1524',
        'card-hover': '#111e33',
        border: '#1a2d4a',
        cyan: '#00d4ff',
        'cyan-dim': '#0099bb',
        green: '#00ff88',
        'green-dim': '#00cc66',
        amber: '#ffaa00',
        red: '#ff4444',
        'text-primary': '#e2e8f0',
        'text-secondary': '#7a9cbf',
        'text-muted': '#4a6a8a',
      },
      fontFamily: {
        mono: ['"Space Mono"', 'monospace'],
        sans: ['"DM Sans"', 'sans-serif'],
      },
      animation: {
        'scan': 'scan 8s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
