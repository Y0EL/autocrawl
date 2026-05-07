<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import CountryDisc from './CountryDisc.vue'
import type { Vendor } from '@/api/types'

/**
 * LiveExhibitorFeed — typewriter ledger.
 *
 *   Mono row indices `001/002/…` flush left, hairline-ruled rows, time-ago
 *   in tabular numerals flush right. New rows arriving in the last 5
 *   seconds carry a vermilion bullet that fades to ink-mute over 4s.
 *
 *   The animation is intentionally minimal: rows do not slide, they
 *   "type-set" with a tiny y-fade. Restraint, not theatre.
 */

const router = useRouter()

const vendors = useQuery({
  queryKey: ['vendors', 'live-feed'],
  queryFn: () => api.vendors({ limit: 12, sort: 'last_enriched_at:desc' }),
  refetchInterval: 5_000,
})

interface Row {
  vendor: Vendor
  iso2: string | null
  fresh: boolean
}

const seenIds = ref<Set<string>>(new Set())
const initialLoadDone = ref(false)

function vendorKey(v: Vendor): string {
  return v.vendor_id || v.domain || v.company_name || ''
}

const rows = computed<Row[]>(() => {
  const items = (vendors.data.value?.items ?? []) as Vendor[]
  return items.map((v) => ({
    vendor: v,
    iso2: v.registrar_country ?? null,
    fresh: initialLoadDone.value && !seenIds.value.has(vendorKey(v)),
  }))
})

watch(
  () => vendors.data.value?.items,
  (items) => {
    if (!items) return
    if (!initialLoadDone.value) {
      for (const v of items as Vendor[]) seenIds.value.add(vendorKey(v))
      initialLoadDone.value = true
      return
    }
    for (const v of items as Vendor[]) {
      const k = vendorKey(v)
      if (!seenIds.value.has(k)) {
        seenIds.value.add(k)
        if (seenIds.value.size > 500) {
          const first = seenIds.value.values().next().value
          if (first) seenIds.value.delete(first)
        }
      }
    }
  },
  { immediate: true },
)

function timeAgo(iso?: string | null): string {
  if (!iso) return '—'
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return '—'
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (s < 60) return `${s}d`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}j`
  const d = Math.floor(h / 24)
  return `${d}h`
}

function open(v: Vendor) {
  if (v.domain) router.push(`/vendors/${v.domain}`)
}
</script>

<template>
  <article class="card">
    <header class="card-head">
      <span class="label">Live · Pengayaan Vendor</span>
      <span class="flex items-center gap-1.5">
        <span class="dot dot-vermilion ink-blink" />
        <span class="label">Stream</span>
      </span>
    </header>

    <ul>
      <li
        v-for="(row, i) in rows"
        :key="vendorKey(row.vendor)"
        class="grid grid-cols-[3rem_1fr_5rem_4.5rem] items-center gap-3 px-5 py-2.5 cursor-pointer hover:bg-paper-2/60"
        :style="{ borderTop: i === 0 ? 'none' : '1px solid rgb(var(--rule) / var(--rule-alpha))' }"
        @click="open(row.vendor)"
      >
        <!-- index + freshness bullet -->
        <div class="flex items-center gap-2 leading-none">
          <span
            class="dot"
            :class="row.fresh ? 'dot-vermilion vermilion-fade' : ''"
            :style="row.fresh ? '' : 'color: rgb(var(--ink-mute))'"
          />
          <span class="font-mono text-[0.625rem] tracking-[0.14em] text-ink-mute">{{ String(i + 1).padStart(3, '0') }}</span>
        </div>

        <!-- name + domain -->
        <div class="min-w-0">
          <span class="block text-[0.9rem] text-ink truncate">
            {{ row.vendor.company_name || row.vendor.domain || '(tanpa nama)' }}
          </span>
          <span class="font-mono text-[0.6875rem] text-ink-mute truncate block">
            {{ row.vendor.domain || '—' }}
          </span>
        </div>

        <!-- country -->
        <CountryDisc
          :country="row.vendor.registrar_country ?? null"
          :iso2="row.iso2"
          :size="14"
        />

        <!-- time ago -->
        <span class="num-display text-right text-[0.875rem] text-ink-2">
          {{ timeAgo(row.vendor.last_enriched_at) }}
        </span>
      </li>
      <li v-if="rows.length === 0" class="px-5 py-6 label text-center">Belum ada pengayaan tercatat.</li>
    </ul>
  </article>
</template>
