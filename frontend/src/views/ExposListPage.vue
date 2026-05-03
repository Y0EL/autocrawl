<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'

const search = ref('')

const { data, isLoading } = useQuery({
  queryKey: ['expos', { search }],
  queryFn: () => api.expos({ search: search.value, limit: 100 }),
})

const items = computed(() => data.value?.items ?? [])

const columns = [
  { key: 'name', label: 'Expo' },
  { key: 'country', label: 'Negara' },
  { key: 'start_date', label: 'Mulai' },
  { key: 'vendor_count', label: 'Vendor', align: 'right' as const },
  { key: 'pdf_count', label: 'PDF', align: 'right' as const },
] as const
</script>

<template>
  <div>
    <PageHeader
      title="Daftar Expo"
      :subtitle="`${items.length} expo terdiscover otomatis lewat multi-source search.`"
    />

    <div class="mb-4">
      <div class="relative">
        <i
          class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
        ></i>
        <input v-model="search" type="text" placeholder="Cari nama expo" class="input pl-9" />
      </div>
    </div>

    <DataTable :items="items" :columns="[...columns]" row-key="expo_id" :loading="isLoading">
      <template #cell-name="{ row }">
        <RouterLink
          :to="`/expos/${row.expo_id}`"
          class="font-medium text-accent-600 hover:underline dark:text-accent-400"
        >
          {{ row.name }}
        </RouterLink>
        <p class="font-mono text-xs text-zinc-500 dark:text-zinc-400">{{ row.expo_id }}</p>
      </template>
      <template #cell-country="{ row }">
        <span class="text-sm">{{ row.country ?? '-' }}</span>
      </template>
      <template #cell-start_date="{ row }">
        <span class="text-sm">{{ row.start_date ?? '-' }}</span>
      </template>
      <template #cell-vendor_count="{ row }">
        <span class="font-semibold tabular-nums">{{ row.vendor_domains?.length ?? 0 }}</span>
      </template>
      <template #cell-pdf_count="{ row }">
        <span class="font-semibold tabular-nums">{{ row.pdf_brochure_urls?.length ?? 0 }}</span>
      </template>
    </DataTable>
  </div>
</template>
