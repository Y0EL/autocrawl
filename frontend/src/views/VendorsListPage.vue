<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Vendor } from '@/api/types'
import PageHeader from '@/components/shell/PageHeader.vue'
import GeoAvatar from '@/components/GeoAvatar.vue'
import TagBadge from '@/components/TagBadge.vue'
import { exportCsv } from '@/composables/useCsvExport'
import { resolveCountry, flagEmoji } from '@/data/country_resolver'

const route = useRoute()
const router = useRouter()

const search = ref('')
const industry = ref('')
const country = ref(typeof route.query.country === 'string' ? route.query.country : '')
const status = ref('enriched')

watch(
  () => route.query.country,
  (next) => { country.value = typeof next === 'string' ? next : '' },
)

const countryFlag = computed(() => {
  if (!country.value) return ''
  const rec = resolveCountry(country.value)
  return rec ? flagEmoji(rec.cca2) : ''
})

function clearCountryFilter() {
  country.value = ''
  const next = { ...route.query }
  delete next.country
  router.replace({ path: route.path, query: next })
}

const countriesQ = useQuery({
  queryKey: ['stats', 'countries-all'],
  queryFn: () => api.stats.countries(50),
})

const { data, isLoading } = useQuery({
  queryKey: ['vendors', { search, industry, country, status }],
  queryFn: () =>
    api.vendors({
      search: search.value,
      industry: industry.value,
      country: country.value,
      status: status.value || undefined,
      limit: 200,
    }),
  refetchInterval: 30000,
  refetchOnWindowFocus: true,
})

const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

function statusTone(s: string): { color: string; label: string } {
  if (s === 'enriched')           return { color: 'ok',    label: 'OK' }
  if (s === 'unresolved')         return { color: 'mute',  label: 'BELUM' }
  if (s === 'enrich_failed')      return { color: 'crit',  label: 'GAGAL' }
  if (s === 'scope_rejected')     return { color: 'warn',  label: 'OFF' }
  if (s === 'validation_rejected')return { color: 'warn',  label: 'TIPIS' }
  return { color: 'mute', label: s.toUpperCase() }
}

function handleExport() {
  exportCsv('vendors_export.csv', items.value, [
    { key: (v) => v.domain ?? '', label: 'Domain' },
    { key: 'company_name', label: 'Company' },
    { key: 'status', label: 'Status' },
    { key: (v) => v.industries.join('|'), label: 'Industries' },
    { key: (v) => v.address?.country ?? '', label: 'Country' },
    { key: 'confidence_score', label: 'Confidence' },
    { key: (v) => v.contacts.find((c) => c.type === 'email')?.value ?? '', label: 'Email' },
    { key: (v) => v.canonical_url ?? '', label: 'URL' },
    { key: (v) => v.expos_seen.join('|'), label: 'Expos' },
  ])
}

function sourceTag(v: Vendor): string {
  const types = new Set((v.source_trail ?? []).map((s) => s.type))
  if (types.has('pdf')) return 'PDF'
  if (types.has('aggregator')) return 'AGR'
  if (types.has('search')) return 'SRC'
  return 'MAN'
}

const stats = computed(() => [
  { label: 'Total', value: total.value.toLocaleString(), tone: 'amber' as const },
  { label: 'Termuat', value: items.value.length, tone: 'mute' as const },
])

const STATUS_OPTIONS = [
  { value: '',                    label: 'Semua status' },
  { value: 'enriched',            label: 'Enriched' },
  { value: 'unresolved',          label: 'Belum resolve' },
  { value: 'enrich_failed',       label: 'Gagal' },
  { value: 'scope_rejected',      label: 'Off-scope' },
  { value: 'validation_rejected', label: 'Tipis' },
]
const INDUSTRY_OPTIONS = [
  { value: '',                label: 'Semua industri' },
  { value: 'defense',         label: 'Defense' },
  { value: 'cybersecurity',   label: 'Cybersecurity' },
  { value: 'law_enforcement', label: 'Law Enforcement' },
  { value: 'surveillance',    label: 'Surveillance' },
  { value: 'aerospace',       label: 'Aerospace' },
]
</script>

<template>
  <div class="flex flex-col">
    <PageHeader
      title="Vendor Registry"
      subtitle="Indeks semua exhibitor yang sudah ter-enriched + yang menunggu resolusi"
      :stats="stats"
    >
      <template #actions>
        <button class="btn btn-ghost h-9" :disabled="!items.length" @click="handleExport">
          <FaIcon :icon="['fas', 'arrow-up-right-from-square']" class="text-[10px]" />
          <span>Export CSV</span>
        </button>
      </template>
    </PageHeader>

    <!-- Active filter chip -->
    <div v-if="country" class="flex items-center justify-between bg-amber/5 rule-b border-amber/30 px-6 py-2.5">
      <div class="flex items-center gap-2 text-[12px]">
        <span class="text-[15px]">{{ countryFlag }}</span>
        <span class="label label-amber">Filter Negara</span>
        <span class="text-ink">{{ country }}</span>
      </div>
      <button class="btn btn-ghost h-7 px-2" type="button" title="Hapus filter" @click="clearCountryFilter">
        <FaIcon :icon="['fas', 'xmark']" class="text-[10px]" />
        Hapus
      </button>
    </div>

    <!-- Filter command bar -->
    <div class="rule-b bg-bg flex items-center gap-2 px-6 py-3">
      <div class="relative flex-1 max-w-md">
        <FaIcon :icon="['fas', 'magnifying-glass']"
                class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[11px] text-ink-mute" />
        <input
          v-model="search"
          type="text"
          placeholder="Cari nama perusahaan atau domain…"
          class="input pl-8 h-9"
        />
      </div>
      <select v-model="status" class="input h-9 w-44">
        <option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <select v-model="industry" class="input h-9 w-44">
        <option v-for="o in INDUSTRY_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <select v-model="country" class="input h-9 w-44">
        <option value="">Semua negara</option>
        <option v-for="c in countriesQ.data.value ?? []" :key="c.country" :value="c.country">
          {{ c.country }} ({{ c.count }})
        </option>
      </select>
      <span v-if="isLoading" class="ml-auto label label-amber flex items-center gap-1.5">
        <span class="dot dot-amber pulse-amber"></span>Memuat…
      </span>
      <span v-else class="ml-auto label label-mute">Live · 30s</span>
    </div>

    <!-- Ledger table -->
    <div class="flex-1 overflow-auto">
      <table v-if="items.length > 0" class="ledger w-full">
        <thead>
          <tr>
            <th class="w-[22%]">Perusahaan</th>
            <th class="w-[14%]">Domain</th>
            <th class="w-[7%] text-center">Status</th>
            <th class="w-[16%]">Industri</th>
            <th class="w-[9%]">Negara</th>
            <th class="w-[14%]">Tech Stack</th>
            <th class="w-[10%] text-right">Confidence</th>
            <th class="w-[8%] text-center">Sumber</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.vendor_id" class="vendor-row cursor-pointer">
            <td>
              <RouterLink
                :to="`/vendors/${row.vendor_id || row.domain}`"
                class="flex items-center gap-3 group"
              >
                <span
                  class="vendor-row__avatar"
                  :data-elite="(row.confidence_score ?? 0) >= 0.9 ? 'true' : 'false'"
                  data-elite-style="inset"
                >
                  <img
                    v-if="row.logo_url"
                    :src="row.logo_url"
                    :alt="row.company_name"
                    class="vendor-row__logo"
                    referrerpolicy="no-referrer"
                  />
                  <GeoAvatar
                    v-else
                    :seed="row.vendor_id || row.domain || row.company_name"
                    :fallback="row.company_name"
                    :size="36"
                  />
                </span>
                <span class="truncate text-ink group-hover:text-amber transition-colors">{{ row.company_name }}</span>
              </RouterLink>
            </td>
            <td>
              <span v-if="row.domain" class="num-display text-[11.5px] text-ink-2 truncate block">{{ row.domain }}</span>
              <span v-else class="text-ink-mute">—</span>
            </td>
            <td class="text-center">
              <span class="pill" :class="`pill-${statusTone(row.status).color}`">
                {{ statusTone(row.status).label }}
              </span>
            </td>
            <td>
              <div class="flex flex-wrap gap-1">
                <TagBadge
                  v-for="tag in row.industries.slice(0, 2)"
                  :key="tag"
                  :raw="tag"
                  size="xs"
                />
                <span v-if="row.industries.length > 2" class="text-[10px] text-ink-mute self-center">+{{ row.industries.length - 2 }}</span>
              </div>
            </td>
            <td>
              <span v-if="row.address?.country" class="flex items-center gap-1.5 text-[12.5px]">
                <span class="text-[14px]">{{ flagEmoji(resolveCountry(row.address.country)?.cca2 ?? '') }}</span>
                <span class="truncate">{{ row.address.country }}</span>
              </span>
              <span v-else class="text-ink-mute">—</span>
            </td>
            <td>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="tech in (row.tech_stack ?? []).slice(0, 3)"
                  :key="tech"
                  class="text-[10px] px-1.5 py-0.5 rounded-[3px] bg-surface-2 text-ink-2 border border-rule"
                >
                  {{ tech }}
                </span>
                <span v-if="!row.tech_stack?.length" class="text-ink-mute">—</span>
              </div>
            </td>
            <td class="text-right">
              <div class="flex items-center justify-end gap-2">
                <div class="w-14 h-1 rounded-[1px] bg-surface-2 overflow-hidden">
                  <div
                    class="h-full bg-amber rounded-[1px]"
                    :style="{ width: `${Math.min(100, Math.round((row.confidence_score ?? 0) * 100))}%` }"
                  />
                </div>
                <span class="num-display text-[11.5px] tabular-nums w-9">
                  {{ ((row.confidence_score ?? 0) * 100).toFixed(0) }}%
                </span>
              </div>
            </td>
            <td class="text-center">
              <span class="pill text-[9.5px]">{{ sourceTag(row) }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else-if="!isLoading" class="flex flex-col items-center justify-center py-24 gap-3">
        <FaIcon :icon="['fas', 'building']" class="text-[28px] text-ink-mute" />
        <span class="label label-mute">Tiada vendor yang cocok dengan filter</span>
        <span class="text-[12px] text-ink-mute">Ubah filter atau jalankan operasi crawl baru</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vendor-row__avatar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 14px;
  overflow: hidden;
  flex-shrink: 0;
  background: rgb(var(--surface-2));
}
.vendor-row__logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 4px;
  background: rgb(var(--surface));
  border-radius: inherit;
}
</style>
