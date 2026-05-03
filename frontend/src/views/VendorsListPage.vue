<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import type { Vendor } from '@/api/types'
import DataTable from '@/components/DataTable.vue'
import CompletenessBar from '@/components/CompletenessBar.vue'
import IndustryBadge from '@/components/IndustryBadge.vue'
import PageHeader from '@/components/PageHeader.vue'
import { exportCsv } from '@/composables/useCsvExport'

const search = ref('')
const industry = ref('')
const country = ref('')

const countriesQ = useQuery({
  queryKey: ['stats', 'countries-all'],
  queryFn: () => api.stats.countries(50),
})

const { data, isLoading } = useQuery({
  queryKey: ['vendors', { search, industry, country }],
  queryFn: () =>
    api.vendors({
      search: search.value,
      industry: industry.value,
      country: country.value,
      limit: 100,
    }),
})

function handleExport() {
  exportCsv('vendors_export.csv', items.value, [
    { key: 'domain', label: 'Domain' },
    { key: 'company_name', label: 'Company' },
    { key: (v) => v.industries.join('|'), label: 'Industries' },
    { key: (v) => v.address?.country ?? '', label: 'Country' },
    { key: 'confidence_score', label: 'Confidence' },
    { key: (v) => v.contacts.find((c) => c.type === 'email')?.value ?? '', label: 'Email' },
    { key: 'canonical_url', label: 'URL' },
    { key: (v) => v.expos_seen.join('|'), label: 'Expos' },
  ])
}

const items = computed(() => data.value?.items ?? [])

const columns = [
  { key: 'company_name', label: 'Perusahaan' },
  { key: 'domain', label: 'Domain' },
  { key: 'industries', label: 'Industri' },
  { key: 'address', label: 'Lokasi' },
  { key: 'confidence_score', label: 'Kelengkapan', width: '180px' },
  { key: 'source', label: 'Sumber', align: 'center' as const },
] as const

const sourceBadge = (vendor: Vendor): { icon: string; label: string; cls: string } => {
  const types = new Set((vendor.source_trail ?? []).map((s) => s.type))
  if (types.has('pdf')) {
    return {
      icon: 'fa-solid fa-file-pdf',
      label: 'PDF',
      cls: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400',
    }
  }
  if (types.has('aggregator')) {
    return {
      icon: 'fa-solid fa-globe',
      label: 'Aggregator',
      cls: 'bg-sky-100 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400',
    }
  }
  return {
    icon: 'fa-solid fa-question',
    label: 'Lainnya',
    cls: 'bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300',
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Daftar Vendor"
      :subtitle="`${items.length} vendor terkoleksi dengan provenance lengkap.`"
    >
      <template #actions>
        <button
          class="btn-ghost h-9 px-3 text-sm"
          :disabled="!items.length"
          @click="handleExport"
        >
          <i class="fa-solid fa-file-csv"></i>
          Export CSV
        </button>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
      <div class="relative flex-1">
        <i
          class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
        ></i>
        <input
          v-model="search"
          type="text"
          placeholder="Cari nama atau domain"
          class="input pl-9"
        />
      </div>
      <select v-model="industry" class="input sm:w-44">
        <option value="">Semua industri</option>
        <option value="defense">Defense</option>
        <option value="cybersecurity">Cybersecurity</option>
        <option value="law_enforcement">Law enforcement</option>
        <option value="surveillance">Surveillance</option>
        <option value="aerospace">Aerospace</option>
      </select>
      <select v-model="country" class="input sm:w-44">
        <option value="">Semua negara</option>
        <option v-for="c in countriesQ.data.value ?? []" :key="c.country" :value="c.country">
          {{ c.country }} ({{ c.count }})
        </option>
      </select>
    </div>

    <DataTable :items="items" :columns="[...columns]" row-key="domain" :loading="isLoading">
      <template #cell-company_name="{ row }">
        <RouterLink
          :to="`/vendors/${row.domain}`"
          class="flex items-center gap-3 font-medium text-accent-600 hover:underline dark:text-accent-400"
        >
          <span
            v-if="!row.logo_url"
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-zinc-100 font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
          >
            {{ row.company_name.charAt(0) }}
          </span>
          <img
            v-else
            :src="row.logo_url"
            :alt="row.company_name"
            class="h-8 w-8 shrink-0 rounded-md object-contain"
            referrerpolicy="no-referrer"
          />
          <span>{{ row.company_name }}</span>
        </RouterLink>
      </template>
      <template #cell-domain="{ row }">
        <span class="font-mono text-xs text-zinc-600 dark:text-zinc-400">{{ row.domain }}</span>
      </template>
      <template #cell-industries="{ row }">
        <div class="flex flex-wrap gap-1">
          <IndustryBadge v-for="tag in row.industries.slice(0, 2)" :key="tag" :tag="tag" />
          <span
            v-if="row.industries.length > 2"
            class="badge bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300"
          >
            +{{ row.industries.length - 2 }}
          </span>
        </div>
      </template>
      <template #cell-address="{ row }">
        <span class="text-sm">
          {{ row.address?.country ?? '-' }}
        </span>
      </template>
      <template #cell-confidence_score="{ row }">
        <CompletenessBar :score="row.confidence_score" show-label />
      </template>
      <template #cell-source="{ row }">
        <span :class="['badge', sourceBadge(row).cls]">
          <i :class="sourceBadge(row).icon"></i>
          {{ sourceBadge(row).label }}
        </span>
      </template>
    </DataTable>
  </div>
</template>
