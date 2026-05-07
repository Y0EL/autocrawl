<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Vendor } from '@/api/types'
import HudPanel from '@/components/HudPanel.vue'
import HudIndustryBadge from '@/components/HudIndustryBadge.vue'
import HudCompletenessBar from '@/components/HudCompletenessBar.vue'
import HudStatusPill from '@/components/HudStatusPill.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'
import { exportCsv } from '@/composables/useCsvExport'
import { resolveCountry, flagEmoji } from '@/data/country_resolver'

const route = useRoute()
const router = useRouter()

const search = ref('')
const industry = ref('')
const country = ref(typeof route.query.country === 'string' ? route.query.country : '')
const status = ref('enriched')

// Keep dropdown synced when navigating to /vendors?country=… from another page.
watch(
  () => route.query.country,
  (next) => {
    country.value = typeof next === 'string' ? next : ''
  },
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
      limit: 100,
    }),
  refetchInterval: 30000,
  refetchOnWindowFocus: true,
})

const statusToneMap: Record<string, 'ok' | 'muted' | 'crit' | 'warn'> = {
  enriched: 'ok',
  unresolved: 'muted',
  enrich_failed: 'crit',
  scope_rejected: 'warn',
  validation_rejected: 'warn',
}

const statusLabelMap: Record<string, string> = {
  enriched: 'OK',
  unresolved: 'BELUM',
  enrich_failed: 'GAGAL',
  scope_rejected: 'OFF-SCOPE',
  validation_rejected: 'TIPIS',
}

const items = computed(() => data.value?.items ?? [])

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

function sourcePill(v: Vendor): { tone: 'crit' | 'info' | 'accent' | 'muted'; label: string } {
  const types = new Set((v.source_trail ?? []).map((s) => s.type))
  if (types.has('pdf')) return { tone: 'crit', label: 'PDF' }
  if (types.has('aggregator')) return { tone: 'info', label: 'AGR' }
  if (types.has('search')) return { tone: 'accent', label: 'SRC' }
  return { tone: 'muted', label: 'MAN' }
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <div
      v-if="country"
      class="flex items-center justify-between rounded-md border border-accent-500/40 bg-accent-500/5 px-3 py-2"
    >
      <div class="flex items-center gap-2 font-mono text-xs text-accent-200">
        <span class="text-base">{{ countryFlag }}</span>
        <span class="uppercase tracking-ops">FILTER NEGARA: {{ country }}</span>
      </div>
      <button
        class="hud-btn-ghost h-7 px-2 text-2xs"
        type="button"
        title="Hapus filter"
        @click="clearCountryFilter"
      >
        <FaIcon :icon="['fas', 'xmark']" class="mr-1 text-2xs" />
        HAPUS
      </button>
    </div>

    <HudPanel title="Filter Vendor" code="VND-FLT">
      <template #actions>
        <button
          class="hud-btn-ghost h-7"
          :disabled="!items.length"
          @click="handleExport"
        >
          <FaIcon :icon="['fas', 'arrow-up-right-from-square']" class="text-2xs" />
          <span>Export CSV</span>
        </button>
      </template>
      <div class="flex flex-col gap-2 md:flex-row md:items-center">
        <div class="relative flex-1">
          <FaIcon
            :icon="['fas', 'magnifying-glass']"
            class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-2xs text-base-400 dark:text-base-500"
          />
          <input
            v-model="search"
            type="text"
            placeholder="CARI NAMA / DOMAIN..."
            class="hud-input pl-7"
          />
        </div>
        <select v-model="status" class="hud-input md:w-44">
          <option value="">SEMUA STATUS</option>
          <option value="enriched">ENRICHED</option>
          <option value="unresolved">BELUM TER-RESOLVE</option>
          <option value="enrich_failed">GAGAL ENRICH</option>
          <option value="scope_rejected">OFF-SCOPE</option>
          <option value="validation_rejected">DATA TIPIS</option>
        </select>
        <select v-model="industry" class="hud-input md:w-48">
          <option value="">SEMUA INDUSTRI</option>
          <option value="defense">DEFENSE</option>
          <option value="cybersecurity">CYBERSECURITY</option>
          <option value="law_enforcement">LAW ENFORCEMENT</option>
          <option value="surveillance">SURVEILLANCE</option>
          <option value="aerospace">AEROSPACE</option>
        </select>
        <select v-model="country" class="hud-input md:w-48">
          <option value="">SEMUA NEGARA</option>
          <option v-for="c in countriesQ.data.value ?? []" :key="c.country" :value="c.country">
            {{ c.country.toUpperCase() }} ({{ c.count }})
          </option>
        </select>
      </div>
    </HudPanel>

    <HudPanel
      :title="`Daftar Vendor (${items.length})`"
      code="VND-LIST"
    >
      <template #actions>
        <span class="hud-chip text-2xs">LIVE 30s</span>
        <span
          v-if="isLoading"
          class="font-mono text-2xs uppercase tracking-ops text-warn-600 dark:text-warn-400"
        >
          MEMUAT...
        </span>
      </template>

      <div v-if="items.length === 0 && !isLoading">
        <HudEmptyState
          icon="building"
          title="Tidak ada vendor"
          hint="Belum ada vendor yang cocok dengan filter saat ini. Coba ubah filter atau jalankan operasi crawl baru."
        />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="hud-table">
          <thead>
            <tr>
              <th class="w-[26%]">Perusahaan</th>
              <th class="w-[16%]">Domain</th>
              <th class="w-[8%] text-center">Status</th>
              <th class="w-[18%]">Industri</th>
              <th class="w-[8%]">Negara</th>
              <th class="w-[10%]">Kelengkapan</th>
              <th class="w-[8%] text-center">Sumber</th>
              <th class="w-[4%] text-center">Bhs</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.vendor_id">
              <td>
                <RouterLink
                  :to="`/vendors/${row.vendor_id || row.domain}`"
                  class="flex items-center gap-2 font-medium text-base-800 hover:text-accent-600 dark:text-base-100 dark:hover:text-accent-300"
                >
                  <span
                    v-if="!row.logo_url"
                    class="flex h-7 w-7 shrink-0 items-center justify-center border border-base-200 bg-base-50 font-mono text-2xs font-semibold text-base-700 dark:border-base-700 dark:bg-base-800 dark:text-base-200"
                  >
                    {{ row.company_name.charAt(0).toUpperCase() }}
                  </span>
                  <img
                    v-else
                    :src="row.logo_url"
                    :alt="row.company_name"
                    class="h-7 w-7 shrink-0 border border-base-200 bg-white object-contain p-0.5 dark:border-base-700 dark:bg-base-800"
                    referrerpolicy="no-referrer"
                  />
                  <span class="truncate">{{ row.company_name }}</span>
                </RouterLink>
              </td>
              <td>
                <span
                  v-if="row.domain"
                  class="hud-mono-num truncate text-2xs text-base-600 dark:text-base-300"
                >
                  {{ row.domain }}
                </span>
                <span
                  v-else
                  class="hud-mono-num truncate text-2xs text-base-400 dark:text-base-500"
                >
                  -
                </span>
              </td>
              <td class="text-center">
                <HudStatusPill
                  :tone="statusToneMap[row.status] ?? 'muted'"
                  :label="statusLabelMap[row.status] ?? row.status.toUpperCase()"
                />
              </td>
              <td>
                <div class="flex flex-wrap gap-1">
                  <HudIndustryBadge
                    v-for="tag in row.industries.slice(0, 2)"
                    :key="tag"
                    :label="tag"
                  />
                  <span v-if="row.industries.length > 2" class="hud-chip">
                    +{{ row.industries.length - 2 }}
                  </span>
                </div>
              </td>
              <td>
                <span class="hud-mono-num text-2xs uppercase">
                  {{ row.address?.country ?? '-' }}
                </span>
              </td>
              <td>
                <HudCompletenessBar :score="row.confidence_score" show-label />
              </td>
              <td class="text-center">
                <HudStatusPill
                  :tone="sourcePill(row).tone"
                  :label="sourcePill(row).label"
                />
              </td>
              <td class="text-center">
                <span
                  class="hud-mono-num text-2xs uppercase"
                  :class="row.language_code === 'id' ? 'text-accent-600 dark:text-accent-300' : 'text-base-400 dark:text-base-500'"
                >
                  {{ row.language_code === 'id' ? 'ID' : 'EN' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </HudPanel>
  </div>
</template>
