<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'

const { data, isLoading } = useQuery({
  queryKey: ['pdfs'],
  queryFn: () => api.pdfs(),
  refetchInterval: 30000,
  refetchOnWindowFocus: true,
})

const items = computed(() => data.value?.items ?? [])

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <HudPanel :title="`Brosur PDF (${items.length})`" code="PDF-LIST">
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
          icon="file-pdf"
          title="Belum ada brosur PDF"
          hint="Operasi crawl akan mengunduh dan dedupe brosur PDF dengan SHA256."
        />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="hud-table">
          <thead>
            <tr>
              <th class="w-[35%]">Berkas</th>
              <th class="w-[20%]">Ekspo</th>
              <th class="w-[10%] text-right">Halaman</th>
              <th class="w-[10%] text-right">Vendor</th>
              <th class="w-[10%] text-right">Ukuran</th>
              <th class="w-[15%]">SHA256</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.sha256">
              <td>
                <a
                  :href="row.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center gap-2 hud-mono-num text-xs text-accent-600 hover:underline dark:text-accent-300"
                >
                  <FaIcon :icon="['fas', 'file-pdf']" class="text-2xs text-crit-500" />
                  <span class="truncate">{{ row.filename }}</span>
                </a>
              </td>
              <td>
                <RouterLink
                  :to="`/expos/${row.expo_id}`"
                  class="hud-mono-num text-2xs text-base-600 hover:text-accent-600 dark:text-base-300 dark:hover:text-accent-300"
                >
                  {{ row.expo_id }}
                </RouterLink>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-xs">{{ row.page_count }}</span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-xs font-semibold text-accent-600 dark:text-accent-300">
                  {{ row.vendors_found }}
                </span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-2xs">{{ formatBytes(row.size_bytes) }}</span>
              </td>
              <td>
                <span class="hud-mono-num text-2xs text-base-400 dark:text-base-500">
                  {{ row.sha256.slice(0, 16) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </HudPanel>
  </div>
</template>
