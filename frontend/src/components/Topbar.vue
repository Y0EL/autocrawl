<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import ThemeToggle from './ThemeToggle.vue'
import StatusIndicator from './StatusIndicator.vue'
import { api } from '@/api/client'

const route = useRoute()
const queryClient = useQueryClient()

const titleMap: Record<string, string> = {
  '/': 'Ringkasan',
  '/vendors': 'Daftar Vendor',
  '/expos': 'Daftar Expo',
  '/pdfs': 'Brosur PDF',
  '/runs': 'Riwayat Run',
}

const title = computed(() => {
  const path = route.path
  if (titleMap[path]) return titleMap[path]
  if (path.startsWith('/vendors/')) return 'Detail Vendor'
  if (path.startsWith('/expos/')) return 'Detail Expo'
  return 'AutoCrawl'
})

const activeQuery = useQuery({
  queryKey: ['runs', 'active'],
  queryFn: api.activeRun,
  refetchInterval: 5000,
})

const isRunning = computed(() => Boolean(activeQuery.data.value?.active))
const submitting = ref(false)

async function triggerRun() {
  if (isRunning.value || submitting.value) return
  submitting.value = true
  try {
    await api.triggerRun('normal')
    toast.success('Run dimulai', {
      description: 'Pipeline crawl jalan di background, dashboard auto refresh saat selesai.',
    })
    queryClient.invalidateQueries({ queryKey: ['runs', 'active'] })
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; data?: { detail?: { message?: string } } } }
    if (e.response?.status === 409) {
      toast.warning('Run sudah aktif', {
        description: e.response.data?.detail?.message ?? 'Tunggu run sekarang selesai.',
      })
    } else {
      toast.error('Gagal trigger run', {
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
    class="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-6 dark:border-zinc-800 dark:bg-zinc-950"
  >
    <div class="flex items-center gap-3">
      <h1 class="text-base font-semibold">{{ title }}</h1>
      <span
        v-if="isRunning"
        class="badge animate-pulse bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30"
      >
        <i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i>
        Run aktif
      </span>
    </div>

    <div class="flex items-center gap-2">
      <StatusIndicator />
      <button
        class="btn-ghost h-9 px-3 text-xs"
        :disabled="isRunning || submitting"
        :title="isRunning ? 'Run sudah aktif' : 'Trigger crawl run sekarang'"
        @click="triggerRun"
      >
        <i :class="submitting ? 'fa-solid fa-circle-notch fa-spin text-xs' : 'fa-solid fa-play text-xs'"></i>
        <span class="text-xs">{{ isRunning ? 'Sedang berjalan' : 'Jalankan run' }}</span>
      </button>
      <ThemeToggle />
    </div>
  </header>
</template>
