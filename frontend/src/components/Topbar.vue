<script setup lang="ts">
import { useRoute, RouterLink } from 'vue-router'
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import HudThemeToggle from './HudThemeToggle.vue'
import HudHeartbeat from './HudHeartbeat.vue'
import HudUptime from './HudUptime.vue'
import HudStatusPill from './HudStatusPill.vue'
import { api } from '@/api/client'

const route = useRoute()
const queryClient = useQueryClient()

interface Crumb {
  label: string
  to?: string
}

const titleMap: Record<string, Crumb[]> = {
  '/': [{ label: 'Pusat Komando' }],
  '/vendors': [{ label: 'Vendor' }],
  '/expos': [{ label: 'Ekspo' }],
  '/pdfs': [{ label: 'Brosur PDF' }],
  '/runs': [{ label: 'Riwayat Operasi' }],
  '/diagnostik': [{ label: 'Diagnostik' }],
}

const breadcrumbs = computed<Crumb[]>(() => {
  const path = route.path
  if (titleMap[path]) return titleMap[path]
  if (path.startsWith('/vendors/')) {
    return [{ label: 'Vendor', to: '/vendors' }, { label: 'Detail' }]
  }
  if (path.startsWith('/expos/')) {
    return [{ label: 'Ekspo', to: '/expos' }, { label: 'Detail' }]
  }
  return [{ label: 'AutoCrawl' }]
})

const activeQuery = useQuery({
  queryKey: ['runs', 'active'],
  queryFn: api.activeRun,
  refetchInterval: 5000,
})

const isRunning = computed(() => Boolean(activeQuery.data.value?.active))
const submitting = ref(false)
const showModeMenu = ref(false)

async function triggerRun(mode: 'dev' | 'normal' | 'aggressive' = 'normal') {
  showModeMenu.value = false
  if (isRunning.value || submitting.value) return
  submitting.value = true
  try {
    await api.triggerRun(mode)
    toast.success('Operasi diluncurkan', {
      description: `Mode ${mode.toUpperCase()} berjalan di background. Dashboard auto refresh saat selesai.`,
    })
    queryClient.invalidateQueries({ queryKey: ['runs', 'active'] })
    queryClient.invalidateQueries({ queryKey: ['vendors'] })
    queryClient.invalidateQueries({ queryKey: ['expos'] })
    queryClient.invalidateQueries({ queryKey: ['pdfs'] })
    queryClient.invalidateQueries({ queryKey: ['runs'] })
    queryClient.invalidateQueries({ queryKey: ['overview'] })
    queryClient.invalidateQueries({ queryKey: ['stats'] })
    queryClient.invalidateQueries({ queryKey: ['exhibitor-refs'] })
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; data?: { detail?: { message?: string } } } }
    if (e.response?.status === 409) {
      toast.warning('Operasi masih aktif', {
        description: e.response.data?.detail?.message ?? 'Tunggu operasi sekarang selesai.',
      })
    } else {
      toast.error('Gagal meluncurkan operasi', {
        description: 'Cek log API container untuk detail.',
      })
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <header
    class="relative z-10 flex h-12 shrink-0 items-center justify-between border-b border-base-200 bg-white px-4 dark:border-base-700 dark:bg-base-900"
  >
    <div class="flex items-center gap-3">
      <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
        SYS://
      </span>
      <nav class="flex items-center gap-1.5 font-mono text-xs uppercase tracking-ops">
        <template v-for="(crumb, i) in breadcrumbs" :key="i">
          <RouterLink
            v-if="crumb.to"
            :to="crumb.to"
            class="text-base-500 hover:text-accent-600 dark:text-base-400 dark:hover:text-accent-300"
          >
            {{ crumb.label }}
          </RouterLink>
          <span v-else class="font-medium text-base-800 dark:text-base-100">
            {{ crumb.label }}
          </span>
          <span v-if="i < breadcrumbs.length - 1" class="text-base-300 dark:text-base-600">/</span>
        </template>
      </nav>
    </div>

    <div class="flex items-center gap-3">
      <HudHeartbeat />
      <span class="hidden h-4 w-px bg-base-200 dark:bg-base-700 sm:inline-block" />
      <HudUptime label="UPTIME" />
    </div>

    <div class="flex items-center gap-2">
      <HudStatusPill
        v-if="isRunning"
        tone="warn"
        label="OPS RUNNING"
        :pulse="true"
      />

      <div class="relative">
        <div class="flex">
          <button
            class="hud-btn-primary h-8 px-3"
            :disabled="isRunning || submitting"
            @click="triggerRun('normal')"
          >
            <FaIcon
              :icon="['fas', submitting ? 'circle-notch' : 'play']"
              :class="submitting ? 'animate-spin text-2xs' : 'text-2xs'"
            />
            <span>{{ isRunning ? 'BERJALAN' : 'ENGAGE' }}</span>
          </button>
          <button
            class="hud-btn-primary h-8 border-l border-accent-700 px-1.5"
            :disabled="isRunning || submitting"
            aria-label="Pilih mode operasi"
            @click="showModeMenu = !showModeMenu"
          >
            <FaIcon :icon="['fas', 'chevron-down']" class="text-2xs" />
          </button>
        </div>

        <Transition
          enter-active-class="transition duration-100"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-75"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="showModeMenu"
            class="absolute right-0 top-9 z-20 w-48 border border-base-200 bg-white shadow-xl dark:border-base-700 dark:bg-base-900"
          >
            <button
              class="flex w-full items-center justify-between px-3 py-2 text-left text-xs hover:bg-accent-500/10"
              @click="triggerRun('dev')"
            >
              <span class="font-mono uppercase tracking-ops">Dev</span>
              <span class="font-mono text-2xs text-base-400 dark:text-base-500">SAMPEL KECIL</span>
            </button>
            <button
              class="flex w-full items-center justify-between border-t border-base-200 px-3 py-2 text-left text-xs hover:bg-accent-500/10 dark:border-base-700"
              @click="triggerRun('normal')"
            >
              <span class="font-mono uppercase tracking-ops">Normal</span>
              <span class="font-mono text-2xs text-base-400 dark:text-base-500">DEFAULT</span>
            </button>
            <button
              class="flex w-full items-center justify-between border-t border-base-200 px-3 py-2 text-left text-xs hover:bg-accent-500/10 dark:border-base-700"
              @click="triggerRun('aggressive')"
            >
              <span class="font-mono uppercase tracking-ops">Agresif</span>
              <span class="font-mono text-2xs text-base-400 dark:text-base-500">FULL THROTTLE</span>
            </button>
          </div>
        </Transition>
      </div>

      <HudThemeToggle />
    </div>
  </header>
</template>
