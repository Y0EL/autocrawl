export const tactical = {
  bg: 'transparent',
  grid: {
    line: {
      dark: '#1E2632',
      light: '#E5EAF1',
    },
  },
  text: {
    primary: { dark: '#E5EAF1', light: '#2A3340' },
    secondary: { dark: '#8F99A8', light: '#5C6878' },
    muted: { dark: '#5C6878', light: '#8F99A8' },
  },
  tooltip: {
    bg: { dark: '#0E1218', light: '#FFFFFF' },
    border: { dark: '#1E2632', light: '#BFC8D4' },
    text: { dark: '#E5EAF1', light: '#2A3340' },
  },
  series: [
    '#FFB800',
    '#06B6D4',
    '#22C55E',
    '#A78BFA',
    '#F472B6',
    '#FB923C',
    '#34D399',
    '#60A5FA',
    '#F59E0B',
    '#EC4899',
    '#10B981',
    '#8B5CF6',
  ],
  accent: '#FFB800',
  ok: '#22C55E',
  warn: '#F59E0B',
  crit: '#EF4444',
  info: '#06B6D4',
}

export function tooltipDefaults(isDark: boolean) {
  return {
    backgroundColor: isDark ? tactical.tooltip.bg.dark : tactical.tooltip.bg.light,
    borderColor: isDark ? tactical.tooltip.border.dark : tactical.tooltip.border.light,
    borderWidth: 1,
    padding: [6, 10],
    textStyle: {
      color: isDark ? tactical.tooltip.text.dark : tactical.tooltip.text.light,
      fontSize: 11,
      fontFamily: 'IBM Plex Mono, monospace',
    },
    extraCssText: 'border-radius: 0; box-shadow: 0 0 0 1px rgba(255,184,0,0.15);',
  }
}

export function axisDefaults(isDark: boolean) {
  const text = isDark ? tactical.text.secondary.dark : tactical.text.secondary.light
  const grid = isDark ? tactical.grid.line.dark : tactical.grid.line.light
  return {
    axisLabel: {
      color: text,
      fontSize: 10,
      fontFamily: 'IBM Plex Mono, monospace',
    },
    axisLine: { lineStyle: { color: grid } },
    axisTick: { lineStyle: { color: grid } },
    splitLine: { lineStyle: { color: grid, type: [2, 4] as [number, number] } },
  }
}
