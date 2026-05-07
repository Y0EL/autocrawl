<script setup lang="ts">
import { computed } from 'vue'
import { useStorage } from '@vueuse/core'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'

interface NavItem {
  to: string
  label: string
  icon: string
  code: string
  countKey?: 'vendors' | 'expos' | 'pdfs' | 'runs'
}

/**
 * Editorial sidebar — collapsible. Indonesian section labels paired
 * with two-letter mono codes that read like a publication's table of
 * contents. FontAwesome icons (registered globally as `<FaIcon>` in
 * main.ts) for visual consistency with the rest of the project.
 */

const items: NavItem[] = [
  { to: '/',            label: 'Pusat Komando', icon: 'gauge-high',         code: 'PK' },
  { to: '/vendors',     label: 'Vendor',        icon: 'building',           code: 'VD', countKey: 'vendors' },
  { to: '/expos',       label: 'Ekspo',         icon: 'flag-checkered',     code: 'EX', countKey: 'expos' },
  { to: '/pdfs',        label: 'Brosur',        icon: 'file-pdf',           code: 'BR', countKey: 'pdfs' },
  { to: '/runs',        label: 'Riwayat',       icon: 'clock-rotate-left',  code: 'RW', countKey: 'runs' },
  { to: '/diagnostik',  label: 'Diagnostik',    icon: 'heart-pulse',        code: 'DG' },
  { to: '/orkestrator', label: 'Orkestrator',   icon: 'circle-nodes',       code: 'OR' },
  { to: '/konfigurasi', label: 'Konfigurasi',   icon: 'sliders',            code: 'KF' },
  { to: '/labs',        label: 'Labs',          icon: 'flask',              code: 'LB' },
]

const collapsed = useStorage('autocrawl-sidebar-collapsed', false)

const overview = useQuery({
  queryKey: ['overview'],
  queryFn: api.overview,
  refetchInterval: 30000,
})
const runsList = useQuery({
  queryKey: ['runs', 'recent', 50],
  queryFn: () => api.runs(50),
  refetchInterval: 30000,
})

const counts = computed(() => ({
  vendors: overview.data.value?.vendors_total ?? null,
  expos: overview.data.value?.expos_total ?? null,
  pdfs: overview.data.value?.pdfs_total ?? null,
  runs: runsList.data.value?.total ?? runsList.data.value?.items?.length ?? null,
}))

function fmtCount(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`
  return String(n)
}
</script>

<template>
  <aside
    class="autocrawl-sidebar bg-paper rule-r relative z-10 flex h-full shrink-0 flex-col transition-[width] duration-200"
    :class="collapsed ? 'w-[60px]' : 'w-[208px]'"
  >
    <!-- Masthead — full when expanded, monogram when collapsed -->
    <div
      class="rule-b flex h-16 items-end pb-3"
      :class="collapsed ? 'justify-center px-0' : 'px-5'"
    >
      <div v-if="!collapsed" class="flex flex-col leading-none">
        <span class="display text-[1.5rem] font-semibold text-ink tracking-tight">
          <span class="text-vermilion">A</span>utocrawl
        </span>
        <span class="label mt-1">Editorial Console</span>
      </div>
      <div
        v-else
        class="flex h-9 w-9 items-center justify-center border border-ink bg-paper"
        title="Autocrawl"
      >
        <span class="display text-[1.125rem] font-semibold leading-none text-vermilion">A</span>
      </div>
    </div>

    <!-- Section heading -->
    <div v-if="!collapsed" class="px-5 pb-1.5 pt-4">
      <span class="label">Bagian</span>
    </div>
    <div v-else class="pt-3 pb-1.5 flex justify-center">
      <span class="dot-rule w-7" />
    </div>

    <!-- Nav -->
    <nav class="flex flex-col">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        custom
        v-slot="{ isActive, navigate }"
      >
        <button
          :class="[
            'group relative flex h-9 w-full items-center transition-colors duration-150',
            collapsed ? 'justify-center px-0' : 'px-5 text-left',
            isActive ? 'bg-paper-2/70' : 'hover:bg-paper-2/40',
          ]"
          :title="collapsed ? `${item.label} · ${item.code}` : undefined"
          @click="navigate"
        >
          <!-- left active rule -->
          <span
            v-if="isActive"
            class="absolute left-0 top-0 h-full w-[2px] bg-ink"
            aria-hidden="true"
          />

          <template v-if="collapsed">
            <FaIcon
              :icon="['fas', item.icon]"
              class="text-[14px]"
              :class="isActive ? 'text-ink' : 'text-ink-2'"
            />
          </template>
          <template v-else>
            <span
              class="font-mono text-[0.625rem] tracking-[0.18em] w-7"
              :class="isActive ? 'text-ink' : 'text-ink-mute'"
            >
              {{ item.code }}
            </span>
            <FaIcon
              :icon="['fas', item.icon]"
              class="text-[12px] mr-2.5"
              :class="isActive ? 'text-ink' : 'text-ink-mute'"
            />
            <span
              class="flex-1 text-[0.8125rem] truncate"
              :class="isActive ? 'text-ink font-medium' : 'text-ink-2'"
            >
              {{ item.label }}
            </span>
            <span
              v-if="item.countKey"
              class="font-mono text-[0.625rem] tabular-nums text-ink-mute"
            >
              {{ fmtCount(counts[item.countKey]) }}
            </span>
          </template>
        </button>
      </RouterLink>
    </nav>

    <!-- spacer -->
    <div class="flex-1"></div>

    <!-- Footer signature + collapse toggle -->
    <div class="rule-t flex flex-col">
      <div
        v-if="!collapsed"
        class="px-5 pt-3 pb-2 flex items-baseline gap-2"
      >
        <span class="dot dot-vermilion -mb-0.5"></span>
        <span class="label-mono">Build 0.3 · Autocrawl</span>
      </div>

      <button
        type="button"
        class="flex h-9 items-center transition-colors hover:bg-paper-2/60"
        :class="collapsed ? 'justify-center px-0' : 'gap-3 px-5'"
        :title="collapsed ? 'Buka sidebar' : 'Tutup sidebar'"
        @click="collapsed = !collapsed"
      >
        <FaIcon
          :icon="['fas', collapsed ? 'angles-right' : 'angles-left']"
          class="text-[12px] text-ink-2"
        />
        <span v-if="!collapsed" class="label">Tutup</span>
      </button>
    </div>
  </aside>
</template>
