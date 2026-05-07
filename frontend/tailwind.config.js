/** @type {import('tailwindcss').Config}
 *
 * Atlas — paper-and-ink token bridge.
 * CSS variables in `src/styles/tokens.css` are the source of truth; this
 * config exposes them as Tailwind utilities so component code can use
 * `text-ink`, `bg-paper`, etc. We also keep a back-compat `base/accent/
 * ok/warn/crit/info` palette so HUD pages that have not been rewritten
 * yet keep compiling.
 */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  darkMode: ['selector', '[data-theme="ink-dark"]'],
  theme: {
    extend: {
      colors: {
        paper:    'rgb(var(--paper) / <alpha-value>)',
        'paper-2':'rgb(var(--paper-2) / <alpha-value>)',
        'paper-edge': 'rgb(var(--paper-edge) / <alpha-value>)',
        ink:      'rgb(var(--ink) / <alpha-value>)',
        'ink-2':  'rgb(var(--ink-2) / <alpha-value>)',
        'ink-mute':'rgb(var(--ink-mute) / <alpha-value>)',
        'accent-ink': 'rgb(var(--accent-ink) / <alpha-value>)',
        'accent-ink-2': 'rgb(var(--accent-ink-2) / <alpha-value>)',
        vermilion:'rgb(var(--vermilion) / <alpha-value>)',
        'gold-leaf':'rgb(var(--gold-leaf) / <alpha-value>)',

        /* Back-compat names for un-ported HUD pages */
        base: {
          50:  'rgb(var(--paper) / <alpha-value>)',
          100: 'rgb(var(--paper-2) / <alpha-value>)',
          200: 'rgb(var(--paper-edge) / <alpha-value>)',
          300: 'rgb(var(--ink-mute) / <alpha-value>)',
          400: 'rgb(var(--ink-mute) / <alpha-value>)',
          500: 'rgb(var(--ink-2) / <alpha-value>)',
          600: 'rgb(var(--ink-2) / <alpha-value>)',
          700: 'rgb(var(--ink) / <alpha-value>)',
          800: 'rgb(var(--ink) / <alpha-value>)',
          900: 'rgb(var(--ink) / <alpha-value>)',
          950: 'rgb(var(--ink) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent-ink) / <alpha-value>)',
          50:  'rgb(var(--accent-ink) / 0.06)',
          100: 'rgb(var(--accent-ink) / 0.12)',
          200: 'rgb(var(--accent-ink) / 0.22)',
          300: 'rgb(var(--accent-ink) / 0.40)',
          400: 'rgb(var(--accent-ink) / 0.65)',
          500: 'rgb(var(--accent-ink) / <alpha-value>)',
          600: 'rgb(var(--accent-ink-2) / <alpha-value>)',
          700: 'rgb(var(--accent-ink-2) / <alpha-value>)',
          800: 'rgb(var(--accent-ink-2) / <alpha-value>)',
          900: 'rgb(var(--accent-ink-2) / <alpha-value>)',
        },
        ok:    { DEFAULT: 'rgb(var(--ok) / <alpha-value>)', 400:'rgb(var(--ok) / 0.7)', 500:'rgb(var(--ok) / <alpha-value>)', 600:'rgb(var(--ok) / <alpha-value>)', 700:'rgb(var(--ok) / <alpha-value>)' },
        warn:  { DEFAULT: 'rgb(var(--warn) / <alpha-value>)', 400:'rgb(var(--warn) / 0.7)', 500:'rgb(var(--warn) / <alpha-value>)', 600:'rgb(var(--warn) / <alpha-value>)', 700:'rgb(var(--warn) / <alpha-value>)' },
        crit:  { DEFAULT: 'rgb(var(--crit) / <alpha-value>)', 400:'rgb(var(--crit) / 0.7)', 500:'rgb(var(--crit) / <alpha-value>)', 600:'rgb(var(--crit) / <alpha-value>)', 700:'rgb(var(--crit) / <alpha-value>)' },
        info:  { DEFAULT: 'rgb(var(--info) / <alpha-value>)', 400:'rgb(var(--info) / 0.7)', 500:'rgb(var(--info) / <alpha-value>)', 600:'rgb(var(--info) / <alpha-value>)', 700:'rgb(var(--info) / <alpha-value>)' },
        ghost: 'rgb(var(--ink-mute) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['"Bricolage Grotesque Variable"', '"Bricolage Grotesque"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono Variable"', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['"Newsreader Variable"', 'Newsreader', 'Georgia', 'serif'],
        serif: ['"Newsreader Variable"', 'Newsreader', 'Georgia', 'serif'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '0.95rem' }],
      },
      letterSpacing: {
        ops: '0.14em',
        display: '-0.015em',
      },
      borderRadius: {
        none: '0',
        sm: '2px',
        DEFAULT: '0',
        lg: '4px',
        xl: '6px',
      },
      boxShadow: {
        hud: 'inset 0 0 0 1px rgb(var(--rule) / var(--rule-alpha))',
        'hud-strong': 'inset 0 0 0 1px rgb(var(--rule) / var(--rule-strong-alpha))',
        panel: 'inset 0 0 0 1px rgb(var(--rule) / var(--rule-alpha))',
      },
      keyframes: {
        'pulse-led': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.55' },
        },
        sweep: {
          '0%':   { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        flicker: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.85' },
        },
      },
      animation: {
        'pulse-led': 'pulse-led 1.6s ease-in-out infinite',
        sweep: 'sweep 2.4s linear infinite',
        flicker: 'flicker 3s ease-in-out infinite',
      },
      backgroundImage: {
        'hud-grid': 'none',
        'hud-grid-light': 'none',
      },
      backgroundSize: {
        'hud-24': '24px 24px',
      },
    },
  },
  plugins: [],
}
