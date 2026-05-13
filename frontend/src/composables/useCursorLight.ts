/**
 * useCursorLight — track pointer position into CSS variables on :root
 * (`--mx` / `--my`) so the gold cursor dot + halo trail follow the
 * cursor. The dot snaps (60ms linear), the halo lags (320ms ease) to
 * create the soft trail. Touch / coarse pointers hide via @media.
 */
import { onBeforeUnmount, onMounted } from 'vue'

export function useCursorLight() {
  let rafId = 0
  let pendingX = 0
  let pendingY = 0
  let active = false

  function setCursorActive(v: boolean) {
    active = v
    if (typeof document !== 'undefined') {
      document.body.setAttribute('data-cursor-active', v ? 'true' : 'false')
    }
  }

  function onMove(e: PointerEvent) {
    pendingX = e.clientX
    pendingY = e.clientY
    if (!active) setCursorActive(true)
    if (rafId) return
    rafId = requestAnimationFrame(() => {
      rafId = 0
      document.documentElement.style.setProperty('--mx', `${pendingX}px`)
      document.documentElement.style.setProperty('--my', `${pendingY}px`)
    })
  }

  function onLeave() { setCursorActive(false) }
  function onEnter() { setCursorActive(true) }

  onMounted(() => {
    if (typeof window === 'undefined') return
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const coarsePointer  = window.matchMedia('(pointer: coarse)').matches
    if (prefersReduced || coarsePointer) {
      document.documentElement.style.setProperty('--mx', '50%')
      document.documentElement.style.setProperty('--my', '0%')
      setCursorActive(false)
      return
    }
    setCursorActive(false) // false until first move
    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('mouseleave', onLeave)
    document.addEventListener('mouseenter', onEnter)
  })

  onBeforeUnmount(() => {
    if (rafId) cancelAnimationFrame(rafId)
    if (typeof window !== 'undefined') {
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('mouseleave', onLeave)
      document.removeEventListener('mouseenter', onEnter)
    }
  })
}
