<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'

const search = ref('')

const { data, isLoading } = useQuery({
  queryKey: ['expos', { search }],
  queryFn: () => api.expos({ search: search.value, limit: 100 }),
  refetchInterval: 30000,
  refetchOnWindowFocus: true,
})

const items = computed(() => data.value?.items ?? [])
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <HudPanel title="Filter Ekspo" code="EXP-FLT">
      <div class="relative">
        <FaIcon
          :icon="['fas', 'magnifying-glass']"
          class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-2xs text-base-400 dark:text-base-500"
        />
        <input
          v-model="search"
          type="text"
          placeholder="CARI NAMA EKSPO..."
          class="hud-input pl-7"
        />
      </div>
    </HudPanel>

    <HudPanel :title="`Daftar Ekspo (${items.length})`" code="EXP-LIST">
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
          icon="flag-checkered"
          title="Belum ada ekspo"
          hint="Discovery agent akan menemukan ekspo baru tiap operasi crawl. Trigger run dari topbar."
        />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="hud-table">
          <thead>
            <tr>
              <th class="w-[40%]">Ekspo</th>
              <th class="w-[15%]">Negara</th>
              <th class="w-[15%]">Tanggal Mulai</th>
              <th class="w-[10%]">Sumber</th>
              <th class="w-[10%] text-right">Vendor</th>
              <th class="w-[10%] text-right">PDF</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.expo_id">
              <td>
                <RouterLink
                  :to="`/expos/${row.expo_id}`"
                  class="font-medium text-base-800 hover:text-accent-600 dark:text-base-100 dark:hover:text-accent-300"
                >
                  {{ row.name }}
                </RouterLink>
                <p class="hud-mono-num truncate text-2xs text-base-400 dark:text-base-500">
                  {{ row.expo_id }}
                </p>
              </td>
              <td>
                <span class="hud-mono-num text-2xs uppercase">
                  {{ row.country ?? '-' }}
                </span>
              </td>
              <td>
                <span class="hud-mono-num text-2xs">
                  {{ row.start_date ?? '-' }}
                </span>
              </td>
              <td>
                <span class="hud-chip">{{ row.source }}</span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-sm font-semibold text-accent-600 dark:text-accent-300">
                  {{ row.vendor_domains?.length ?? 0 }}
                </span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-sm font-semibold text-info-600 dark:text-info-400">
                  {{ row.pdf_brochure_urls?.length ?? 0 }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </HudPanel>
  </div>
</template>
