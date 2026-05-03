import { useDark, useToggle } from '@vueuse/core'

const isDark = useDark({
  storageKey: 'autocrawl-theme',
  selector: 'html',
  attribute: 'class',
  valueDark: 'dark',
  valueLight: 'light',
  initialValue: 'dark',
})

const toggleDark = useToggle(isDark)

export function useTheme() {
  return { isDark, toggleDark }
}
