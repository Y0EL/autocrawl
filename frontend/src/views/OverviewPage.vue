<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import IntelStatCard from '@/components/IntelStatCard.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'
import IndustryPieChart from '@/components/charts/IndustryPieChart.vue'
import SourceTypePieChart from '@/components/charts/SourceTypePieChart.vue'
import VendorTimelineChart from '@/components/charts/VendorTimelineChart.vue'
import WorldHeatChart from '@/components/charts/WorldHeatChart.vue'

const search = ref('')
const days = ref(30)

const overviewQ = useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: 30000 })
const countriesQ = useQuery({ queryKey: ['stats', 'countries'], queryFn: () => api.stats.countries(30) })
const sourcesQ = useQuery({ queryKey: ['stats', 'source-types'], queryFn: api.stats.sourceTypes })
const timelineQ = useQuery({ queryKey: ['stats', 'timeline', days], queryFn: () => api.stats.timeline(days.value) })
const recentQ = useQuery({
  queryKey: ['vendors', 'recent'],
  queryFn: () => api.vendors({ limit: 12, sort: 'last_enriched_at:desc' }),
  refetchInterval: 60000,
})

const overview = computed(() => overviewQ.data.value)
const recentVendors = computed(() => recentQ.data.value?.items ?? [])

const sparklineData = computed(() => {
  const t = timelineQ.data.value ?? []
  return t.map((p) => p.vendors_added)
})

const phasePct = computed(() => {
  const o = overview.value
  if (!o || !o.phase_2_threshold) return 0
  return Math.round((o.vendors_total / o.phase_2_threshold) * 100)
})

const phaseColor = computed(() => {
  const p = phasePct.value
  if (p >= 75) return '#10b981'
  if (p >= 40) return '#f59e0b'
  return '#ef4444'
})

const dateLabel = computed(() => {
  const now = new Date()
  const past = new Date(now.getTime() - days.value * 86400000)
  const fmt = (d: Date) =>
    d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: '2-digit' })
  return `${fmt(past)} ke ${fmt(now)}`
})

function shiftDays(delta: number) {
  days.value = Math.max(7, Math.min(365, days.value + delta))
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
      <div class="relative flex-1">
        <i
          class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
        ></i>
        <input
          v-model="search"
          type="text"
          placeholder="Cari vendor, expo, atau domain"
          class="input border-zinc-800 bg-zinc-900/50 pl-9 text-zinc-100 placeholder-zinc-600"
        />
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-ghost h-9 px-3 text-xs" @click="shiftDays(-7)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <button class="btn-ghost h-9 px-3 text-xs" @click="shiftDays(-1)">
          <i class="fa-solid fa-angle-left"></i>
        </button>
        <span
          class="rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-2 font-mono text-xs text-zinc-300"
        >
          {{ dateLabel }}
        </span>
        <button class="btn-ghost h-9 px-3 text-xs" @click="shiftDays(1)">
          <i class="fa-solid fa-angle-right"></i>
        </button>
        <button class="btn-ghost h-9 px-3 text-xs" @click="shiftDays(7)">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <div class="grid gap-3 lg:grid-cols-12">
      <div class="space-y-3 lg:col-span-9">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <IntelStatCard
            label="Vendor"
            hint="Total terkoleksi"
            :value="overview?.vendors_total ?? 0"
            :emphasis="`/ ${overview?.phase_2_threshold ?? 100}`"
            :series="sparklineData"
            color="#6366f1"
          />
          <IntelStatCard
            label="Expo"
            hint="Discovery dari multi sumber"
            :value="overview?.expos_total ?? 0"
            :series="sparklineData.length ? sparklineData : [3, 5, 8, 6, 12, 10, 14]"
            color="#10b981"
            type="line"
          />
          <IntelStatCard
            label="PDF Brosur"
            hint="Diunduh dan diekstrak"
            :value="overview?.pdfs_total ?? 0"
            :series="sparklineData.length ? sparklineData : [1, 0, 2, 1, 3, 1, 2]"
            color="#f59e0b"
          />
          <div
            class="card flex flex-col justify-between border-zinc-800 bg-zinc-900/50 p-4"
          >
            <div>
              <div class="text-base font-semibold text-zinc-100">Phase 2</div>
              <p class="mt-0.5 text-xs text-zinc-500">Progress menuju paid tier unlock</p>
            </div>
            <div class="flex items-end gap-3">
              <span
                class="text-4xl font-bold tabular-nums leading-none tracking-tight"
                :style="{ color: phaseColor }"
              >
                {{ phasePct }}%
              </span>
              <div class="mb-1 flex-1">
                <div class="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
                  <div
                    class="h-full rounded-full transition-all"
                    :style="{ width: `${Math.min(phasePct, 100)}%`, backgroundColor: phaseColor }"
                  ></div>
                </div>
                <p class="mt-1 text-xs text-zinc-500">
                  Sisa {{ Math.max(0, (overview?.phase_2_threshold ?? 100) - (overview?.vendors_total ?? 0)) }} vendor
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="grid gap-3 lg:grid-cols-2">
          <div class="card border-zinc-800 bg-zinc-900/50 p-4">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-zinc-100">Distribusi Industri</h3>
              <span class="text-xs text-zinc-500">vendor per tag</span>
            </div>
            <IndustryPieChart
              :data="overview?.industry_breakdown ?? []"
              :loading="overviewQ.isLoading.value"
            />
          </div>
          <div class="card border-zinc-800 bg-zinc-900/50 p-4">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-zinc-100">Sumber Penemuan</h3>
              <span class="text-xs text-zinc-500">PDF / Aggregator / Search</span>
            </div>
            <SourceTypePieChart
              :data="sourcesQ.data.value ?? []"
              :loading="sourcesQ.isLoading.value"
            />
          </div>
        </div>

        <div class="card border-zinc-800 bg-zinc-900/50 p-4">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-zinc-100">Akumulasi Vendor</h3>
            <span class="text-xs text-zinc-500">{{ days }} hari terakhir</span>
          </div>
          <VendorTimelineChart
            :data="timelineQ.data.value ?? []"
            :loading="timelineQ.isLoading.value"
          />
        </div>

        <div class="card border-zinc-800 bg-zinc-900/50 p-4">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-zinc-100">Sebaran Geografis</h3>
            <span class="text-xs text-zinc-500">berdasarkan registrar domain</span>
          </div>
          <WorldHeatChart :data="countriesQ.data.value ?? []" />
        </div>
      </div>

      <div class="lg:col-span-3 lg:row-span-2">
        <ActivityFeed :vendors="recentVendors" />
      </div>
    </div>
  </div>
</template>
