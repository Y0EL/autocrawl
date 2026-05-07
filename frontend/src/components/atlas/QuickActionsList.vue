<script setup lang="ts">
import { computed } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'

const router = useRouter()
const queryClient = useQueryClient()

const activeQuery = useQuery({
  queryKey: ['runs', 'active'],
  queryFn: api.activeRun,
  refetchInterval: 5000,
})

const isRunning = computed(() => Boolean(activeQuery.data.value?.active))

interface Action {
  group: string
  label: string
  hint: string
  icon: string
  run: () => void
}

const actions = computed<Action[]>(() => [
  {
    group: 'Operasi',
    label: isRunning.value ? 'Operasi berjalan' : 'Luncurkan operasi · Normal',
    hint: isRunning.value ? 'Tunggu drain · cek Bengkel' : 'Run normal mode',
    icon: isRunning.value ? 'radio' : 'play',
    run: async () => {
      if (isRunning.value) { router.push('/orkestrator'); return }
      try {
        await api.triggerRun('normal')
        toast.success('Operasi diluncurkan')
        queryClient.invalidateQueries({ queryKey: ['runs', 'active'] })
      } catch {
        toast.error('Gagal meluncurkan operasi')
      }
    },
  },
  { group: 'Operasi', label: 'Riwayat operasi', hint: 'Telusuri jejak run', icon: 'history',  run: () => router.push('/runs') },
  { group: 'Vendor',  label: 'Daftar vendor',   hint: 'Indeks lengkap',     icon: 'building-2', run: () => router.push('/vendors') },
  { group: 'Vendor',  label: 'Labs · Fusi',     hint: 'Konsolidasi LLM',    icon: 'flask-conical', run: () => router.push('/labs') },
  { group: 'Ekspo',   label: 'Daftar ekspo',    hint: 'Per negara · per tema', icon: 'flag',  run: () => router.push('/expos') },
  { group: 'Ekspo',   label: 'Brosur PDF',      hint: 'Arsip cetak',        icon: 'book-open', run: () => router.push('/pdfs') },
  { group: 'Sistem',  label: 'Konfigurasi',     hint: 'Aturan & prompt',    icon: 'sliders-horizontal', run: () => router.push('/konfigurasi') },
  { group: 'Sistem',  label: 'Diagnostik',      hint: 'Health & uptime',    icon: 'activity', run: () => router.push('/diagnostik') },
])

const grouped = computed(() => {
  const map = new Map<string, Action[]>()
  for (const a of actions.value) {
    if (!map.has(a.group)) map.set(a.group, [])
    map.get(a.group)!.push(a)
  }
  return [...map.entries()]
})
</script>

<template>
  <article class="card">
    <header class="card-head">
      <span class="label">Aksi Cepat</span>
      <span class="font-mono text-[0.625rem] tracking-[0.14em] text-ink-mute">⌘ + K</span>
    </header>

    <div>
      <div v-for="([groupName, groupActions], gi) in grouped" :key="groupName">
        <div
          class="px-5 py-1.5"
          :style="gi === 0 ? '' : 'border-top: 1px solid rgb(var(--rule) / var(--rule-alpha));'"
        >
          <span class="label">{{ groupName }}</span>
        </div>
        <ul>
          <li
            v-for="a in groupActions"
            :key="a.label"
            class="group flex items-center gap-3 px-5 py-2.5 cursor-pointer hover:bg-paper-2/60"
            style="border-top: 1px solid rgb(var(--rule) / var(--rule-alpha));"
            @click="a.run()"
          >
            <Icon :name="a.icon" :size="16" class="text-ink-2 shrink-0" />
            <div class="min-w-0 flex-1">
              <span class="block text-[0.875rem] text-ink truncate">{{ a.label }}</span>
              <span class="font-mono text-[0.625rem] tracking-[0.06em] text-ink-mute truncate block">
                {{ a.hint }}
              </span>
            </div>
            <Icon name="chevron-right" :size="14" class="text-ink-mute opacity-0 group-hover:opacity-100 transition-opacity" />
          </li>
        </ul>
      </div>
    </div>
  </article>
</template>
