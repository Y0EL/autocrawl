<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'

/**
 * IndustryDonut — hand-rolled SVG donut chart, ink strokes only.
 *
 *   Refusing ECharts here so we have full control over the engraving
 *   feel: 1px arcs in the accent ink, paper gaps between segments,
 *   a Newsreader center label, no fills, no shadows.
 */

const industries = useQuery({
  queryKey: ['stats', 'industries'],
  queryFn: api.stats.industries,
  refetchInterval: 60_000,
})

interface Segment {
  tag: string
  count: number
  start: number
  end: number
  d: string
}

const size = 200
const cx = size / 2
const cy = size / 2
const rOuter = 86
const rInner = 60

function arcPath(startAngle: number, endAngle: number): string {
  const a0 = startAngle - Math.PI / 2
  const a1 = endAngle - Math.PI / 2
  const large = endAngle - startAngle > Math.PI ? 1 : 0
  const x0 = cx + rOuter * Math.cos(a0)
  const y0 = cy + rOuter * Math.sin(a0)
  const x1 = cx + rOuter * Math.cos(a1)
  const y1 = cy + rOuter * Math.sin(a1)
  const xi1 = cx + rInner * Math.cos(a1)
  const yi1 = cy + rInner * Math.sin(a1)
  const xi0 = cx + rInner * Math.cos(a0)
  const yi0 = cy + rInner * Math.sin(a0)
  return [
    `M ${x0} ${y0}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${x1} ${y1}`,
    `L ${xi1} ${yi1}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${xi0} ${yi0}`,
    'Z',
  ].join(' ')
}

const segments = computed<Segment[]>(() => {
  const rows = (industries.data.value ?? []).slice().sort((a, b) => (b.count ?? 0) - (a.count ?? 0))
  const top = rows.slice(0, 5)
  const rest = rows.slice(5)
  const restSum = rest.reduce((s, r) => s + (r.count ?? 0), 0)
  const merged = restSum > 0 ? [...top, { tag: 'Lainnya', count: restSum }] : top
  const total = merged.reduce((s, r) => s + (r.count ?? 0), 0) || 1
  let acc = 0
  const out: Segment[] = []
  for (const r of merged) {
    const span = ((r.count ?? 0) / total) * Math.PI * 2
    const start = acc
    const end = acc + span - 0.02 // small paper gap between segments
    acc += span
    if (end > start) {
      out.push({
        tag: r.tag,
        count: r.count ?? 0,
        start,
        end,
        d: arcPath(start, end),
      })
    }
  }
  return out
})

const total = computed(() => segments.value.reduce((s, x) => s + x.count, 0))

const palette = [
  'rgb(var(--accent-ink))',
  'rgb(var(--ink))',
  'rgb(var(--ink-2))',
  'rgb(var(--ink-mute))',
  'rgb(var(--gold-leaf))',
  'rgb(var(--vermilion))',
]
</script>

<template>
  <article class="card">
    <header class="card-head">
      <span class="label">Koneksi · Per Industri</span>
      <span class="font-mono text-[0.625rem] tracking-[0.14em] text-ink-mute">DONUT</span>
    </header>

    <div class="flex items-center justify-between gap-4 px-5 py-4">
      <svg :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size" class="shrink-0">
        <!-- ring guide -->
        <circle :cx="cx" :cy="cy" :r="rOuter" fill="none" stroke="rgb(var(--ink) / 0.10)" stroke-width="0.6" />
        <circle :cx="cx" :cy="cy" :r="rInner" fill="none" stroke="rgb(var(--ink) / 0.10)" stroke-width="0.6" />
        <!-- segments -->
        <path
          v-for="(seg, i) in segments"
          :key="seg.tag"
          :d="seg.d"
          :fill="palette[i % palette.length]"
          fill-opacity="0.92"
          stroke="rgb(var(--paper))"
          stroke-width="1.5"
        >
          <title>{{ seg.tag }}: {{ seg.count.toLocaleString() }}</title>
        </path>
        <!-- center label -->
        <text
          :x="cx"
          :y="cy - 4"
          text-anchor="middle"
          font-family="Newsreader Variable, Newsreader, Georgia, serif"
          font-size="28"
          font-weight="500"
          fill="rgb(var(--ink))"
          font-feature-settings="'tnum','lnum'"
        >
          {{ total.toLocaleString() }}
        </text>
        <text
          :x="cx"
          :y="cy + 14"
          text-anchor="middle"
          font-family="JetBrains Mono Variable, JetBrains Mono, monospace"
          font-size="9"
          letter-spacing="0.18em"
          fill="rgb(var(--ink-mute))"
        >
          KONEKSI
        </text>
      </svg>

      <ul class="flex-1 min-w-0 space-y-1.5">
        <li
          v-for="(seg, i) in segments"
          :key="seg.tag"
          class="grid grid-cols-[10px_1fr_3.5rem] items-center gap-2"
        >
          <span
            class="block w-2.5 h-2.5"
            :style="{ background: palette[i % palette.length] }"
          />
          <span class="text-[0.8125rem] text-ink-2 truncate">{{ seg.tag }}</span>
          <span class="num-display text-right text-[0.8125rem]">{{ seg.count.toLocaleString() }}</span>
        </li>
      </ul>
    </div>
  </article>
</template>
