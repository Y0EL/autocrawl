<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'
import { resolveCountry, flagEmoji } from '@/data/country_resolver'

const route = useRoute()
const router = useRouter()
const search = ref('')

const countryFilter = computed(() => {
  const q = route.query.country
  return typeof q === 'string' ? q : null
})

const countryFlag = computed(() => {
  const c = countryFilter.value
  if (!c) return ''
  const rec = resolveCountry(c)
  return rec ? flagEmoji(rec.cca2) : ''
})

const { data, isLoading } = useQuery({
  queryKey: ['expos', { search, country: countryFilter }],
  queryFn: () =>
    api.expos({
      search: search.value,
      country: countryFilter.value ?? undefined,
      limit: 100,
    }),
  refetchInterval: 30000,
  refetchOnWindowFocus: true,
})

const items = computed(() => data.value?.items ?? [])

function clearCountryFilter() {
  const next = { ...route.query }
  delete next.country
  router.replace({ path: route.path, query: next })
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <div
      v-if="countryFilter"
      class="flex items-center justify-between rounded-md border border-accent-500/40 bg-accent-500/5 px-3 py-2"
    >
      <div class="flex items-center gap-2 font-mono text-xs text-accent-200">
        <span class="text-base">{{ countryFlag }}</span>
        <span class="uppercase tracking-ops">FILTER NEGARA: {{ countryFilter }}</span>
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
