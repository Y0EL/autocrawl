<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import RunsModeBarChart from '@/components/charts/RunsModeBarChart.vue'

const { data, isLoading } = useQuery({
  queryKey: ['runs'],
  queryFn: () => api.runs(50),
})

const modeStats = useQuery({
  queryKey: ['stats', 'runs-mode'],
  queryFn: () => api.stats.runsMode(30),
})

const items = computed(() => data.value?.items ?? [])

const columns = [
  { key: 'run_id', label: 'Run ID' },
  { key: 'mode', label: 'Mode' },
  { key: 'started_at', label: 'Mulai' },
  { key: 'duration', label: 'Durasi' },
  { key: 'expos_discovered', label: 'Expo', align: 'right' as const },
  { key: 'vendors_enriched', label: 'Vendor', align: 'right' as const },
  { key: 'failures', label: 'Gagal', align: 'right' as const },
] as const

const modeStyle = (mode: string): string => {
  switch (mode) {
    case 'aggressive':
      return 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400'
    case 'normal':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
    case 'dev':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'
    default:
      return 'bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300'
  }
}

const formatDuration = (started: string, finished: string | null | undefined): string => {
  if (!finished) return '-'
  const ms = new Date(finished).getTime() - new Date(started).getTime()
  if (ms < 0) return '-'
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000)
  return `${minutes}m ${seconds}s`
}

const formatDate = (iso: string): string =>
  new Date(iso).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'medium' })
</script>

<template>
  <div>
    <PageHeader
      title="Riwayat Run"
      :subtitle="`${items.length} run tercatat. Phase 2 unlock saat counter mencapai 100 vendor.`"
    />

    <div class="card mb-6 p-5">
      <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        <i class="fa-solid fa-chart-column mr-1"></i> Distribusi Mode 30 Hari Terakhir
      </h3>
      <RunsModeBarChart
        :data="modeStats.data.value ?? []"
        :loading="modeStats.isLoading.value"
      />
    </div>

    <DataTable :items="items" :columns="[...columns]" row-key="run_id" :loading="isLoading">
      <template #cell-run_id="{ row }">
        <span class="font-mono text-xs text-zinc-600 dark:text-zinc-300">
          {{ row.run_id.slice(0, 28) }}
        </span>
      </template>
      <template #cell-mode="{ row }">
        <span :class="['badge', modeStyle(row.mode)]">{{ row.mode }}</span>
      </template>
      <template #cell-started_at="{ row }">
        <span class="text-sm">{{ formatDate(row.started_at) }}</span>
      </template>
      <template #cell-duration="{ row }">
        <span class="font-mono text-sm">{{ formatDuration(row.started_at, row.finished_at) }}</span>
      </template>
      <template #cell-expos_discovered="{ row }">
        <span class="tabular-nums">{{ row.expos_discovered }}</span>
      </template>
      <template #cell-vendors_enriched="{ row }">
        <span class="font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
          {{ row.vendors_enriched }}
        </span>
      </template>
      <template #cell-failures="{ row }">
        <span
          :class="[
            'tabular-nums',
            row.failures > 0
              ? 'font-semibold text-rose-600 dark:text-rose-400'
              : 'text-zinc-400 dark:text-zinc-600',
          ]"
        >
          {{ row.failures }}
        </span>
      </template>
    </DataTable>
  </div>
</template>
