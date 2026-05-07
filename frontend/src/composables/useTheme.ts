import { useStorage } from '@vueuse/core'
import { computed, watchEffect } from 'vue'

type ThemeName = 'paper' | 'ink-dark'

const themeRef = useStorage<ThemeName>('atlas-theme', 'paper')

if (typeof document !== 'undefined') {
  watchEffect(() => {
    document.documentElement.setAttribute('data-theme', themeRef.value)
  })
}

const isDark = computed({
  get: () => themeRef.value === 'ink-dark',
  set: (v: boolean) => { themeRef.value = v ? 'ink-dark' : 'paper' },
})

function toggleDark() {
  isDark.value = !isDark.value
}

export function useTheme() {
  return { isDark, toggleDark, theme: themeRef }
}
