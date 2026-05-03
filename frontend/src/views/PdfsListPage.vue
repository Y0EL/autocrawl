<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'

const { data, isLoading } = useQuery({
  queryKey: ['pdfs'],
  queryFn: () => api.pdfs(),
})

const items = computed(() => data.value?.items ?? [])

const columns = [
  { key: 'filename', label: 'Berkas' },
  { key: 'expo_id', label: 'Expo' },
  { key: 'page_count', label: 'Halaman', align: 'right' as const },
  { key: 'vendors_found', label: 'Vendor', align: 'right' as const },
  { key: 'size_bytes', label: 'Ukuran', align: 'right' as const },
  { key: 'sha256', label: 'SHA256' },
] as const

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
</script>

<template>
  <div>
    <PageHeader
      title="Brosur PDF"
      :subtitle="`${items.length} brosur PDF terdownload dengan dedup SHA256.`"
    />

    <DataTable :items="items" :columns="[...columns]" row-key="sha256" :loading="isLoading">
      <template #cell-filename="{ row }">
        <a
          :href="row.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-2 font-medium text-accent-600 hover:underline dark:text-accent-400"
        >
          <i class="fa-solid fa-file-pdf text-rose-500"></i>
          <span class="font-mono text-sm">{{ row.filename }}</span>
        </a>
      </template>
      <template #cell-expo_id="{ row }">
        <RouterLink
          :to="`/expos/${row.expo_id}`"
          class="font-mono text-xs text-zinc-600 hover:text-accent-600 dark:text-zinc-400 dark:hover:text-accent-400"
        >
          {{ row.expo_id }}
        </RouterLink>
      </template>
      <template #cell-page_count="{ row }">
        <span class="tabular-nums">{{ row.page_count }}</span>
      </template>
      <template #cell-vendors_found="{ row }">
        <span class="font-semibold tabular-nums">{{ row.vendors_found }}</span>
      </template>
      <template #cell-size_bytes="{ row }">
        <span class="font-mono text-xs">{{ formatBytes(row.size_bytes) }}</span>
      </template>
      <template #cell-sha256="{ row }">
        <span class="font-mono text-xs text-zinc-500 dark:text-zinc-400">
          {{ row.sha256.slice(0, 16) }}
        </span>
      </template>
    </DataTable>
  </div>
</template>
