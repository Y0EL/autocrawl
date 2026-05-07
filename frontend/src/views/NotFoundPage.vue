<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'

const route = useRoute()
/**
 * 404 — Off the Map.
 *
 * A constellation of stipple dots in the rough shape of a question mark,
 * so the not-found page reads as part of the cartographic universe and
 * not a generic SaaS error screen.
 */
function rng(seed: number) {
  let t = seed >>> 0
  return () => {
    t = (t + 0x6D2B79F5) >>> 0
    let x = t
    x = Math.imul(x ^ (x >>> 15), x | 1)
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

const stippleDots = computed(() => {
  const r = rng(0x404)
  // Sample points along an analytic question-mark curve, then jitter.
  const out: { cx: number; cy: number; rad: number; opacity: number }[] = []
  const stem = (t: number) => ({
    x: 80 + 18 * Math.cos(2.6 + t * Math.PI),
    y: 30 + t * 80,
  })
  const dot = { x: 80, y: 130, w: 12, h: 12 }

  // Curve segment
  for (let i = 0; i < 380; i++) {
    const t = i / 380
    const p = stem(t)
    const jx = p.x + (r() - 0.5) * 6
    const jy = p.y + (r() - 0.5) * 6
    out.push({ cx: jx, cy: jy, rad: 0.6 + r() * 0.7, opacity: 0.4 + r() * 0.5 })
  }
  // Dot at the bottom
  for (let i = 0; i < 60; i++) {
    const a = r() * Math.PI * 2
    const rr = r() * 5
    out.push({
      cx: dot.x + Math.cos(a) * rr,
      cy: dot.y + Math.sin(a) * rr,
      rad: 0.6 + r() * 0.7,
      opacity: 0.55 + r() * 0.4,
    })
  }
  return out
})
</script>

<template>
  <section class="atlas-404 flex h-full flex-col items-center justify-center gap-10 px-8 py-16">
    <!-- Stipple constellation -->
    <svg width="160" height="160" viewBox="0 0 160 160" aria-hidden="true">
      <circle cx="80" cy="80" r="74" fill="none" stroke="rgb(var(--ink) / 0.10)" stroke-width="0.6" stroke-dasharray="1 4" />
      <circle
        v-for="(d, i) in stippleDots"
        :key="i"
        :cx="d.cx"
        :cy="d.cy"
        :r="d.rad"
        :fill="`rgb(var(--ink) / ${d.opacity.toFixed(2)})`"
      />
    </svg>

    <div class="flex flex-col items-center gap-3 text-center">
      <span class="label">Edisi 404 · Halaman tidak ditemukan</span>
      <h1 class="display text-[3rem] leading-[1] tracking-tight">
        <span class="text-vermilion">T</span>ersesat dari <em class="italic">peta</em>
      </h1>
      <p class="font-mono text-[0.75rem] tabular-nums text-ink-mute">
        PATH · {{ route.fullPath }}
      </p>
      <p class="max-w-md text-[0.95rem] text-ink-2 mt-1">
        Halaman ini tidak terdaftar di indeks Autocrawl. Silakan kembali ke pusat
        komando atau telusuri bagian melalui sidebar.
      </p>
    </div>

    <RouterLink to="/" class="btn btn-accent h-10">
      <Icon name="gauge" :size="14" />
      <span>Kembali ke Pusat Komando</span>
    </RouterLink>
  </section>
</template>
