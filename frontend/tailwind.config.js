/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        base: {
          50: '#F4F6FA',
          100: '#E5EAF1',
          200: '#BFC8D4',
          300: '#8F99A8',
          400: '#5C6878',
          500: '#3D4754',
          600: '#2A3340',
          700: '#1E2632',
          800: '#151B25',
          900: '#0E1218',
          950: '#07090C',
        },
        accent: {
          DEFAULT: '#FFB800',
          50: '#FFF4D6',
          100: '#FFE9AD',
          200: '#FFD86B',
          300: '#FFC533',
          400: '#FFB800',
          500: '#FFB800',
          600: '#CC9300',
          700: '#996F00',
          800: '#664A00',
          900: '#332500',
        },
        ok: {
          DEFAULT: '#22C55E',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D',
        },
        warn: {
          DEFAULT: '#F59E0B',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309',
        },
        crit: {
          DEFAULT: '#EF4444',
          400: '#F87171',
          500: '#EF4444',
          600: '#DC2626',
          700: '#B91C1C',
        },
        info: {
          DEFAULT: '#06B6D4',
          400: '#22D3EE',
          500: '#06B6D4',
          600: '#0891B2',
          700: '#0E7490',
        },
        ghost: '#334155',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['IBM Plex Mono', 'JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['IBM Plex Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      letterSpacing: {
        ops: '0.08em',
      },
      borderRadius: {
        none: '0',
        sm: '2px',
        DEFAULT: '2px',
      },
      boxShadow: {
        hud: '0 0 0 1px rgba(255, 184, 0, 0.15)',
        'hud-strong': '0 0 0 1px rgba(255, 184, 0, 0.45), 0 0 24px -6px rgba(255, 184, 0, 0.25)',
        panel: '0 1px 0 0 rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0, 0, 0, 0.04)',
      },
      keyframes: {
        'pulse-led': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 currentColor' },
          '50%': { opacity: '0.55', boxShadow: '0 0 0 4px transparent' },
        },
        'sweep': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        'flicker': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.85' },
        },
      },
      animation: {
        'pulse-led': 'pulse-led 1.6s ease-in-out infinite',
        sweep: 'sweep 2.4s linear infinite',
        flicker: 'flicker 3s ease-in-out infinite',
      },
      backgroundImage: {
        'hud-grid':
          'linear-gradient(to right, rgba(143, 153, 168, 0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(143, 153, 168, 0.06) 1px, transparent 1px)',
        'hud-grid-light':
          'linear-gradient(to right, rgba(60, 71, 84, 0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(60, 71, 84, 0.06) 1px, transparent 1px)',
      },
      backgroundSize: {
        'hud-24': '24px 24px',
      },
    },
  },
  plugins: [],
}
