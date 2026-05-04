<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudStatusPill from '@/components/HudStatusPill.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'
import RunsModeBarChart from '@/components/charts/RunsModeBarChart.vue'

const { data, isLoading } = useQuery({
  queryKey: ['runs'],
  queryFn: () => api.runs(50),
  refetchInterval: 5000,
  refetchOnWindowFocus: true,
})

const modeStats = useQuery({
  queryKey: ['stats', 'runs-mode'],
  queryFn: () => api.stats.runsMode(30),
})

const items = computed(() => data.value?.items ?? [])

function formatDuration(started: string, finished: string | null | undefined): string {
  if (!finished) return 'JALAN'
  const ms = new Date(finished).getTime() - new Date(started).getTime()
  if (ms < 0) return '-'
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000)
  return `${minutes}m ${seconds.toString().padStart(2, '0')}s`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'medium' })
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

function modeTone(mode: string): 'crit' | 'accent' | 'info' | 'muted' {
  if (mode === 'aggressive') return 'crit'
  if (mode === 'normal') return 'accent'
  if (mode === 'dev') return 'info'
  return 'muted'
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <HudPanel title="Distribusi Mode 30 Hari" code="OPS-MODE">
      <RunsModeBarChart :data="modeStats.data.value ?? []" :loading="modeStats.isLoading.value" />
    </HudPanel>

    <HudPanel :title="`Riwayat Operasi (${items.length})`" code="OPS-HIST">
      <template #actions>
        <span class="hud-chip text-2xs text-warn-600 dark:text-warn-400">LIVE 5s</span>
        <span
          v-if="isLoading"
          class="font-mono text-2xs uppercase tracking-ops text-warn-600 dark:text-warn-400"
        >
          MEMUAT...
        </span>
      </template>

      <div v-if="items.length === 0 && !isLoading">
        <HudEmptyState
          icon="clock-rotate-left"
          title="Belum ada operasi"
          hint="Trigger ENGAGE di topbar untuk meluncurkan operasi crawl."
        />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="hud-table">
          <thead>
            <tr>
              <th class="w-[8%]">Status</th>
              <th class="w-[20%]">Run ID</th>
              <th class="w-[10%]">Mode</th>
              <th class="w-[18%]">Mulai</th>
              <th class="w-[10%] text-right">Durasi</th>
              <th class="w-[8%] text-right">Ekspo</th>
              <th class="w-[10%] text-right">Vendor</th>
              <th class="w-[8%] text-right">Gagal</th>
              <th class="w-[8%] text-right">Token</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.run_id">
              <td>
                <HudStatusPill
                  :tone="runTone(row)"
                  :label="runLabel(row)"
                  :pulse="!row.finished_at"
                />
              </td>
              <td>
                <span class="hud-mono-num text-2xs text-base-700 dark:text-base-200">
                  {{ row.run_id.slice(0, 24) }}
                </span>
              </td>
              <td>
                <HudStatusPill :tone="modeTone(row.mode)" :label="row.mode.toUpperCase()" />
              </td>
              <td>
                <span class="hud-mono-num text-2xs">{{ formatDate(row.started_at) }}</span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-2xs">
                  {{ formatDuration(row.started_at, row.finished_at) }}
                </span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-xs">{{ row.expos_discovered }}</span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-xs font-semibold text-accent-600 dark:text-accent-300">
                  {{ row.vendors_enriched }}
                </span>
              </td>
              <td class="text-right">
                <span
                  class="hud-mono-num text-xs"
                  :class="row.failures > 0 ? 'font-semibold text-crit-600 dark:text-crit-400' : 'text-base-400 dark:text-base-500'"
                >
                  {{ row.failures }}
                </span>
              </td>
              <td class="text-right">
                <span class="hud-mono-num text-2xs text-base-500 dark:text-base-400">
                  {{ row.openai_tokens_used ? Math.round(row.openai_tokens_used / 1000) + 'k' : '-' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </HudPanel>
  </div>
</template>
