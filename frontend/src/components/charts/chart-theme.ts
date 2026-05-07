/**
 * Autocrawl pen-and-ink chart theme.
 *
 * Re-export the same module shape the old `tactical` HUD theme used so
 * existing chart consumers do not need code changes — only the values
 * are different. Strokes, no fills. JetBrains Mono labels at 10/11px.
 * Single ink + accent ink + vermilion punctuation, optional gold-leaf
 * for tertiary series.
 *
 * Note: ECharts does not let us inject CSS variables at runtime, so
 * these are baked literal hex values. They mirror tokens.css. If you
 * change the token palette, mirror the changes here.
 */

const PAPER  = '#F4EFE6'
const INK    = '#141210'
const INK_2  = '#3A342D'
const INK_M  = '#7A7167'
const RULE   = 'rgba(20,18,16,0.18)'
const RULE_S = 'rgba(20,18,16,0.32)'
const ACCENT = '#10302E'
const VERM   = '#B5321A'
const GOLD   = '#9E7C2E'

export const tactical = {
  bg: 'transparent',
  grid: {
    line: { dark: RULE, light: RULE },
  },
  text: {
    primary:   { dark: INK,    light: INK },
    secondary: { dark: INK_2,  light: INK_2 },
    muted:     { dark: INK_M,  light: INK_M },
  },
  tooltip: {
    bg:     { dark: PAPER, light: PAPER },
    border: { dark: RULE_S, light: RULE_S },
    text:   { dark: INK,   light: INK },
  },
  series: [ACCENT, INK, INK_2, INK_M, GOLD, VERM],
  accent: ACCENT,
  ok:    '#166347',
  warn:  GOLD,
  crit:  VERM,
  info:  ACCENT,
}

const FONT_MONO = '"JetBrains Mono Variable", "JetBrains Mono", ui-monospace, monospace'

export function tooltipDefaults(_isDark: boolean) {
  return {
    backgroundColor: PAPER,
    borderColor: RULE_S,
    borderWidth: 1,
    padding: [8, 12],
    textStyle: {
      color: INK,
      fontSize: 11,
      fontFamily: FONT_MONO,
    },
    extraCssText: 'border-radius: 0; box-shadow: 0 6px 18px rgba(0,0,0,0.06);',
  }
}

export function axisDefaults(_isDark: boolean) {
  return {
    axisLabel: {
      color: INK_M,
      fontSize: 10,
      fontFamily: FONT_MONO,
      fontFeatureSettings: 'tnum, lnum',
    },
    axisLine: { lineStyle: { color: RULE_S, width: 1 } },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: RULE, type: [1, 4] as [number, number] } },
  }
}
