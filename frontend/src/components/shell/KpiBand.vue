<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import { useNumberTicker } from '@/composables/useNumberTicker'

/**
 * KpiBand — the band of large editorial numbers that sits below the topbar
 * across the entire app. Five tiles: total exhibitors (VND), expos (EXP),
 * brochures (PDF), trails / runs (TRL), ops uptime (OPS).
 *
 * Tiles are separated by hairlines, never by gaps. Numbers render in
 * Newsreader tabular lining-figures so totals at 4xl read like a printed
 * stat block on a magazine spread.
 */

const overview = useQuery({
  queryKey: ['overview'],
  queryFn: api.overview,
  refetchInterval: 30000,
})

const timeline = useQuery({
  queryKey: ['stats', 'timeline', 30],
  queryFn: () => api.stats.timeline(30),
  refetchInterval: 60000,
})

const runsList = useQuery({
  queryKey: ['runs', 'recent', 50],
  queryFn: () => api.runs(50),
  refetchInterval: 30000,
})

const runsActive = useQuery({
  queryKey: ['runs', 'active'],
  queryFn: api.activeRun,
  refetchInterval: 5000,
})

const totals = computed(() => ({
  vendors: overview.data.value?.vendors_total ?? 0,
  expos: overview.data.value?.expos_total ?? 0,
  pdfs: overview.data.value?.pdfs_total ?? 0,
  runs: runsList.data.value?.total ?? runsList.data.value?.items?.length ?? 0,
}))

const deltas = computed(() => {
  const points = timeline.data.value ?? []
  if (points.length < 2) return { vendors: 0 }
  const half = Math.floor(points.length / 2)
  const earlySum = points.slice(0, half).reduce((s, p) => s + (p.vendors_added ?? 0), 0)
  const lateSum = points.slice(half).reduce((s, p) => s + (p.vendors_added ?? 0), 0)
  if (earlySum === 0) return { vendors: lateSum > 0 ? 100 : 0 }
  return { vendors: ((lateSum - earlySum) / Math.max(earlySum, 1)) * 100 }
})

const vendorsRef = computed(() => totals.value.vendors)
const exposRef = computed(() => totals.value.expos)
const pdfsRef = computed(() => totals.value.pdfs)
const runsRef = computed(() => totals.value.runs)

const tickedVendors = useNumberTicker(vendorsRef)
const tickedExpos = useNumberTicker(exposRef)
const tickedPdfs = useNumberTicker(pdfsRef)
const tickedRuns = useNumberTicker(runsRef)

const opsState = computed<'live' | 'idle'>(() => (runsActive.data.value?.active ? 'live' : 'idle'))

function fmt(n: number): string {
  return n.toLocaleString('en-US')
}
function pctSign(p: number): { value: string; positive: boolean } {
  const sign = p >= 0 ? '+' : ''
  return { value: `${sign}${p.toFixed(1)}%`, positive: p >= 0 }
}
</script>

<template>
  <section class="kpi-band rule-b bg-paper relative z-30 grid grid-cols-5">
    <!-- Tile: Vendors -->
    <div class="rule-r flex flex-col px-6 py-4">
      <div class="flex items-baseline justify-between">
        <span class="label">VND · Exhibitors</span>
        <span class="font-mono text-[0.625rem] tracking-[0.14em] text-ink-mute">30D</span>
      </div>
      <div class="mt-1 flex items-baseline gap-2.5">
        <span class="num-display text-4xl leading-none">{{ fmt(tickedVendors) }}</span>
        <span
          class="font-mono text-[0.6875rem] tabular-nums"
          :class="pctSign(deltas.vendors).positive ? 'text-accent-ink' : 'text-vermilion'"
        >
          <Icon
            :name="pctSign(deltas.vendors).positive ? 'arrow-up-right' : 'arrow-down-right'"
            :size="11"
            class="inline-block -mt-0.5"
          />
          {{ pctSign(deltas.vendors).value }}
        </span>
      </div>
    </div>

    <!-- Tile: Expos -->
    <div class="rule-r flex flex-col px-6 py-4">
      <span class="label">EXP · Pameran</span>
      <div class="mt-1 flex items-baseline gap-2.5">
        <span class="num-display text-4xl leading-none">{{ fmt(tickedExpos) }}</span>
        <span class="font-mono text-[0.6875rem] tabular-nums text-ink-mute">edisi</span>
      </div>
    </div>

    <!-- Tile: PDFs -->
    <div class="rule-r flex flex-col px-6 py-4">
      <span class="label">BR · Brosur</span>
      <div class="mt-1 flex items-baseline gap-2.5">
        <span class="num-display text-4xl leading-none">{{ fmt(tickedPdfs) }}</span>
        <span class="font-mono text-[0.6875rem] tabular-nums text-ink-mute">arsip</span>
      </div>
    </div>

    <!-- Tile: Runs -->
    <div class="rule-r flex flex-col px-6 py-4">
      <span class="label">RW · Riwayat</span>
      <div class="mt-1 flex items-baseline gap-2.5">
        <span class="num-display text-4xl leading-none">{{ fmt(tickedRuns) }}</span>
        <span class="font-mono text-[0.6875rem] tabular-nums text-ink-mute">jejak</span>
      </div>
    </div>

    <!-- Tile: Ops state -->
    <div class="flex flex-col px-6 py-4">
      <span class="label">OPS · Status</span>
      <div class="mt-1 flex items-center gap-2.5">
        <span
          class="dot"
          :class="opsState === 'live' ? 'dot-vermilion' : 'dot-accent'"
        ></span>
        <span class="display text-[2rem] leading-none">
          {{ opsState === 'live' ? 'Live' : 'Tenang' }}
        </span>
      </div>
    </div>
  </section>
</template>
