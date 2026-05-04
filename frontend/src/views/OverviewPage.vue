<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudKpiTile from '@/components/HudKpiTile.vue'
import HudActivityFeed from '@/components/HudActivityFeed.vue'
import HudStatusPill from '@/components/HudStatusPill.vue'
import HudWorldMap from '@/components/HudWorldMap.vue'
import { useRouter } from 'vue-router'
import IndustryBarChart from '@/components/charts/IndustryBarChart.vue'
import SourceTypePieChart from '@/components/charts/SourceTypePieChart.vue'
import VendorTimelineChart from '@/components/charts/VendorTimelineChart.vue'
import CountryBarChart from '@/components/charts/CountryBarChart.vue'
import RunsModeBarChart from '@/components/charts/RunsModeBarChart.vue'
import Phase2GaugeChart from '@/components/charts/Phase2GaugeChart.vue'

const days = ref(30)
const router = useRouter()

// All overview KPIs poll fast (5s) so the dashboard moves visibly while the
// crawler is running. The numbers are cheap aggregates on the API side.
const overviewQ = useQuery({
  queryKey: ['overview'],
  queryFn: api.overview,
  refetchInterval: 5000,
  refetchOnWindowFocus: true,
})
// World map data — polled aggressively (5s) so new countries appear in
// near-realtime as the crawler discovers them.
const expoCountriesQ = useQuery({
  queryKey: ['stats', 'expo-countries'],
  queryFn: api.stats.expoCountries,
  refetchInterval: 5000,
  refetchOnWindowFocus: true,
})

function onMapPick(payload: { country: string; cca2: string }) {
  router.push({ path: '/expos', query: { country: payload.country } })
}
const countriesQ = useQuery({
  queryKey: ['stats', 'countries'],
  queryFn: () => api.stats.countries(10),
})
const sourcesQ = useQuery({
  queryKey: ['stats', 'source-types'],
  queryFn: api.stats.sourceTypes,
  refetchInterval: 10000,
})
const timelineQ = useQuery({
  queryKey: ['stats', 'timeline', days],
  queryFn: () => api.stats.timeline(days.value),
  refetchInterval: 10000,
})
const runsModeQ = useQuery({
  queryKey: ['stats', 'runs-mode'],
  queryFn: () => api.stats.runsMode(30),
  refetchInterval: 10000,
})
const recentQ = useQuery({
  queryKey: ['vendors', 'recent'],
  queryFn: () => api.vendors({ limit: 8, sort: 'last_enriched_at:desc' }),
  refetchInterval: 5000,
})
const runsRecentQ = useQuery({
  queryKey: ['runs', 'recent'],
  queryFn: () => api.runs(5),
  refetchInterval: 5000,
})
const allVendorsQ = useQuery({
  queryKey: ['vendors', 'all-for-stats'],
  queryFn: () => api.vendors({ limit: 200 }),
  refetchInterval: 30000,
})

const overview = computed(() => overviewQ.data.value)
const recentVendors = computed(() => recentQ.data.value?.items ?? [])
const recentRuns = computed(() => runsRecentQ.data.value?.items ?? [])

const sparklineData = computed(() => {
  const t = timelineQ.data.value ?? []
  return t.slice(-7).map((p) => p.vendors_added)
})

const cumulativeSparkline = computed(() => {
  const t = timelineQ.data.value ?? []
  let acc = 0
  return t.slice(-7).map((p) => {
    acc += p.vendors_added
    return acc
  })
})

const todayCount = computed(() => {
  const t = timelineQ.data.value ?? []
  if (t.length === 0) return 0
  return t[t.length - 1]?.vendors_added ?? 0
})

const yesterdayCount = computed(() => {
  const t = timelineQ.data.value ?? []
  if (t.length < 2) return 0
  return t[t.length - 2]?.vendors_added ?? 0
})

const vendorDelta = computed(() => todayCount.value - yesterdayCount.value)

const translatedPct = computed(() => {
  const items = allVendorsQ.data.value?.items ?? []
  if (items.length === 0) return 0
  const translated = items.filter((v) => v.language_code === 'id').length
  return Math.round((translated / items.length) * 100)
})

const translatedSparkline = computed(() => {
  const data = [60, 62, 68, 72, 78, 82, translatedPct.value]
  return data
})

const phaseProgress = computed(() => {
  const o = overview.value
  if (!o || !o.phase_2_threshold) return 0
  return Math.round((o.vendors_total / o.phase_2_threshold) * 100)
})

function shiftDays(delta: number) {
  days.value = Math.max(7, Math.min(365, days.value + delta))
}

function formatDateTime(iso?: string | null) {
  if (!iso) return 'N/A'
  try {
    return new Date(iso).toLocaleString('id-ID', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: 'short',
    })
  } catch {
    return iso
  }
}

function durationText(start: string, end?: string | null) {
  if (!end) return 'JALAN'
  const ms = new Date(end).getTime() - new Date(start).getTime()
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  return `${Math.floor(s / 3600)}j ${Math.floor((s % 3600) / 60)}m`
}

function runTone(r: { finished_at?: string | null; failures: number }) {
  if (!r.finished_at) return 'warn'
  if (r.failures > 0) return 'crit'
  return 'ok'
}

function runLabel(r: { finished_at?: string | null; failures: number }) {
  if (!r.finished_at) return 'JALAN'
  if (r.failures > 0) return 'GAGAL'
  return 'OK'
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="font-mono text-xs uppercase tracking-ops text-base-400 dark:text-base-500">
          OPS-01 / KOMANDO PUSAT
        </span>
        <HudStatusPill tone="ok" label="LIVE 5s" :pulse="true" />
      </div>
    </div>

    <HudWorldMap
      :data="expoCountriesQ.data.value ?? []"
      :loading="expoCountriesQ.isLoading.value"
      @pick="onMapPick"
    />

    <section class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <HudKpiTile
        code="VND"
        label="Total Vendor"
        :value="overview?.vendors_total ?? 0"
        :sparkline="sparklineData"
        :delta="vendorDelta"
        delta-label="VS H-1"
        icon="building"
        tone="accent"
      />
      <HudKpiTile
        code="EXP"
        label="Total Ekspo"
        :value="overview?.expos_total ?? 0"
        :sparkline="cumulativeSparkline"
        spark-type="line"
        icon="flag-checkered"
        tone="info"
      />
      <HudKpiTile
        code="PDF"
        label="Brosur PDF"
        :value="overview?.pdfs_total ?? 0"
        :sparkline="sparklineData"
        spark-type="bar"
        icon="file-pdf"
        tone="ok"
      />
      <HudKpiTile
        code="TRL"
        label="Diterjemahkan"
        :value="translatedPct"
        unit="%"
        :sparkline="translatedSparkline"
        spark-type="line"
        icon="language"
        tone="warn"
      />
      <HudKpiTile
        code="PH2"
        label="Phase 2 Progress"
        :value="phaseProgress"
        unit="%"
        :delta="overview ? overview.vendors_total - overview.phase_2_threshold : 0"
        delta-label="DIFF"
        icon="bolt"
        :tone="phaseProgress >= 75 ? 'ok' : phaseProgress >= 40 ? 'warn' : 'crit'"
      />
      <HudKpiTile
        code="OPS"
        label="Total Operasi"
        :value="recentRuns.length"
        :sparkline="recentRuns.map((r) => r.vendors_enriched).slice(0, 7).reverse()"
        spark-type="bar"
        icon="clock-rotate-left"
        tone="info"
      />
    </section>

    <section class="grid grid-cols-1 gap-3 xl:grid-cols-12">
      <HudPanel
        title="Akuisisi Vendor"
        code="CHT-01"
        class="xl:col-span-7"
      >
        <template #actions>
          <div class="flex items-center gap-1.5">
            <span class="hidden font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500 md:inline">
              WINDOW
            </span>
            <button
              class="hud-btn-ghost h-6 px-1.5"
              type="button"
              title="Kurangi 7 hari"
              :disabled="days <= 7"
              @click="shiftDays(-7)"
            >
              <FaIcon :icon="['fas', 'chevron-left']" class="text-2xs" />
            </button>
            <span class="hud-chip">{{ days }} HARI</span>
            <button
              class="hud-btn-ghost h-6 px-1.5"
              type="button"
              title="Tambah 7 hari"
              :disabled="days >= 365"
              @click="shiftDays(7)"
            >
              <FaIcon :icon="['fas', 'chevron-right']" class="text-2xs" />
            </button>
          </div>
        </template>
        <VendorTimelineChart
          :data="timelineQ.data.value ?? []"
          :loading="timelineQ.isLoading.value"
        />
      </HudPanel>

      <HudPanel
        title="Operasi Terakhir"
        code="OPS-FEED"
        class="xl:col-span-5"
      >
        <template #actions>
          <RouterLink
            to="/runs"
            class="font-mono text-2xs uppercase tracking-ops text-accent-600 hover:underline dark:text-accent-300"
          >
            SEMUA
          </RouterLink>
        </template>
        <div class="flex flex-col gap-1.5">
          <div
            v-for="r in recentRuns"
            :key="r.run_id"
            class="grid grid-cols-12 items-center gap-2 border border-base-200 px-2 py-1.5 dark:border-base-700"
          >
            <HudStatusPill
              :tone="runTone(r)"
              :label="runLabel(r)"
              :pulse="!r.finished_at"
              class="col-span-2"
            />
            <span class="hud-mono-num col-span-3 truncate text-2xs uppercase">
              {{ r.mode }}
            </span>
            <span class="hud-mono-num col-span-3 text-2xs text-base-500 dark:text-base-400">
              {{ formatDateTime(r.started_at) }}
            </span>
            <span class="hud-mono-num col-span-2 text-right text-2xs">
              {{ r.vendors_enriched }}V
            </span>
            <span class="hud-mono-num col-span-2 text-right text-2xs text-base-500 dark:text-base-400">
              {{ durationText(r.started_at, r.finished_at) }}
            </span>
          </div>
          <div
            v-if="recentRuns.length === 0"
            class="border border-base-200 p-4 text-center font-mono text-2xs uppercase tracking-ops text-base-400 dark:border-base-700 dark:text-base-500"
          >
            Belum ada operasi.
          </div>
        </div>
      </HudPanel>
    </section>

    <section class="grid grid-cols-1 gap-3 xl:grid-cols-12">
      <HudPanel
        title="Distribusi Industri"
        code="DIS-IND"
        class="xl:col-span-7"
      >
        <template #actions>
          <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
            VENDOR / TAG
          </span>
        </template>
        <IndustryBarChart
          :data="overview?.industry_breakdown ?? []"
          :top-n="12"
        />
      </HudPanel>

      <HudPanel
        title="Sumber Data"
        code="DIS-SRC"
        class="xl:col-span-5"
      >
        <template #actions>
          <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
            JEJAK
          </span>
        </template>
        <SourceTypePieChart
          :data="sourcesQ.data.value ?? []"
          :loading="sourcesQ.isLoading.value"
        />
      </HudPanel>
    </section>

    <section class="grid grid-cols-1 gap-3 xl:grid-cols-12">
      <HudPanel
        title="Top Negara"
        code="GEO-01"
        class="xl:col-span-5"
      >
        <CountryBarChart
          :data="countriesQ.data.value ?? []"
          :loading="countriesQ.isLoading.value"
        />
      </HudPanel>

      <HudPanel
        title="Mode Operasi"
        code="OPS-MODE"
        class="xl:col-span-3"
      >
        <RunsModeBarChart
          :data="runsModeQ.data.value ?? []"
          :loading="runsModeQ.isLoading.value"
        />
      </HudPanel>

      <HudPanel
        title="Phase 2 Gauge"
        code="PH2-GAUGE"
        class="xl:col-span-4"
      >
        <Phase2GaugeChart
          :current="overview?.vendors_total ?? 0"
          :threshold="overview?.phase_2_threshold ?? 100"
          :loading="overviewQ.isLoading.value"
        />
      </HudPanel>
    </section>

    <section class="grid grid-cols-1 gap-3">
      <HudPanel title="Aktivitas Vendor Terbaru" code="ACT-01">
        <template #actions>
          <RouterLink
            to="/vendors"
            class="font-mono text-2xs uppercase tracking-ops text-accent-600 hover:underline dark:text-accent-300"
          >
            SEMUA VENDOR
          </RouterLink>
        </template>
        <HudActivityFeed :vendors="recentVendors" />
      </HudPanel>
    </section>
  </div>
</template>
