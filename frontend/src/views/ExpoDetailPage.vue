<script setup lang="ts">
import { ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'

const props = defineProps<{ expoId: string }>()
const queryClient = useQueryClient()

const deepening = ref(false)

const { data, isLoading, isError } = useQuery({
  queryKey: ['expo', () => props.expoId],
  queryFn: () => api.expo(props.expoId),
  refetchInterval: () => (deepening.value ? 5000 : false),
})

async function deepenExpo() {
  if (!data.value || deepening.value) return
  deepening.value = true
  toast.info('Perdalam ekspo diluncurkan', {
    description: 'Re-extract aggregator + PDF + push refs ke pipeline. Vendor akan nambah seiring proses.',
  })
  try {
    await api.deepenExpo(props.expoId)
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['expo', () => props.expoId] })
      queryClient.invalidateQueries({ queryKey: ['expos'] })
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
      queryClient.invalidateQueries({ queryKey: ['exhibitor-refs'] })
    }, 8000)
    setTimeout(() => {
      deepening.value = false
    }, 90000)
  } catch {
    deepening.value = false
    toast.error('Gagal meluncurkan deepen', {
      description: 'Cek log API container.',
    })
  }
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <RouterLink
      to="/expos"
      class="inline-flex w-fit items-center gap-2 font-mono text-2xs uppercase tracking-ops text-base-500 hover:text-accent-600 dark:text-base-400 dark:hover:text-accent-300"
    >
      <FaIcon :icon="['fas', 'chevron-left']" class="text-2xs" />
      KEMBALI KE DAFTAR EKSPO
    </RouterLink>

    <div v-if="isLoading" class="hud-panel animate-pulse p-8">
      <div class="h-6 w-1/3 bg-base-200 dark:bg-base-700" />
    </div>

    <HudPanel v-else-if="isError" code="ERR" title="Ekspo tidak ditemukan">
      <HudEmptyState
        icon="circle-xmark"
        title="Target tidak ditemukan"
        hint="Ekspo dengan ID ini belum terdiscover."
      />
    </HudPanel>

    <template v-else-if="data">
      <HudPanel :title="data.name" code="EXP-INFO">
        <template #actions>
          <span class="hud-mono-num text-2xs text-base-400 dark:text-base-500">
            {{ data.expo_id }}
          </span>
          <button
            class="hud-btn-primary h-7"
            :disabled="deepening"
            @click="deepenExpo"
          >
            <FaIcon
              :icon="['fas', deepening ? 'circle-notch' : 'crosshairs']"
              :class="deepening ? 'animate-spin text-2xs' : 'text-2xs'"
            />
            <span>{{ deepening ? 'MEMPERDALAM...' : 'PERDALAM SEKARANG' }}</span>
          </button>
        </template>

        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-xs md:grid-cols-4">
          <div class="flex flex-col gap-0.5">
            <dt class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">NEGARA</dt>
            <dd class="font-medium text-base-800 dark:text-base-100">{{ data.country ?? '-' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">LOKASI</dt>
            <dd class="font-medium text-base-800 dark:text-base-100">{{ data.location ?? '-' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">TGL MULAI</dt>
            <dd class="hud-mono-num text-base-800 dark:text-base-100">{{ data.start_date ?? '-' }}</dd>
          </div>
          <div class="flex flex-col gap-0.5">
            <dt class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">TGL SELESAI</dt>
            <dd class="hud-mono-num text-base-800 dark:text-base-100">{{ data.end_date ?? '-' }}</dd>
          </div>
        </dl>

        <div v-if="data.topics?.length" class="mt-3 flex flex-wrap gap-1.5">
          <span v-for="t in data.topics" :key="t" class="hud-chip">{{ t }}</span>
        </div>

        <div class="mt-3 flex flex-wrap gap-2">
          <a
            v-if="data.aggregator_url"
            :href="data.aggregator_url"
            target="_blank"
            rel="noopener noreferrer"
            class="hud-btn-ghost h-7"
          >
            <FaIcon :icon="['fas', 'globe']" class="text-2xs" />
            <span>AGREGATOR</span>
          </a>
          <a
            v-if="data.official_url"
            :href="data.official_url"
            target="_blank"
            rel="noopener noreferrer"
            class="hud-btn-ghost h-7"
          >
            <FaIcon :icon="['fas', 'link']" class="text-2xs" />
            <span>SITUS RESMI</span>
          </a>
        </div>
      </HudPanel>

      <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <HudPanel
          :title="`Vendor Terkoleksi (${data.vendor_domains?.length ?? 0})`"
          code="EXP-VND"
        >
          <div v-if="data.vendor_domains?.length" class="flex flex-col">
            <RouterLink
              v-for="d in data.vendor_domains"
              :key="d"
              :to="`/vendors/${d}`"
              class="flex items-center justify-between border-b border-base-100 px-2 py-2 hud-mono-num text-xs text-accent-600 hover:bg-accent-500/5 dark:border-base-800 dark:text-accent-300"
            >
              <span class="truncate">{{ d }}</span>
              <FaIcon :icon="['fas', 'chevron-right']" class="text-2xs" />
            </RouterLink>
          </div>
          <HudEmptyState
            v-else
            icon="building"
            title="Belum ada vendor"
            hint="Operasi crawl akan mengisi daftar vendor untuk ekspo ini."
          />
        </HudPanel>

        <HudPanel
          :title="`Brosur PDF (${data.pdf_brochure_urls?.length ?? 0})`"
          code="EXP-PDF"
        >
          <div v-if="data.pdf_brochure_urls?.length" class="flex flex-col">
            <a
              v-for="url in data.pdf_brochure_urls"
              :key="url"
              :href="url"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center gap-2 border-b border-base-100 px-2 py-2 hud-mono-num text-xs text-accent-600 hover:bg-accent-500/5 dark:border-base-800 dark:text-accent-300"
            >
              <FaIcon :icon="['fas', 'file-pdf']" class="shrink-0 text-2xs" />
              <span class="truncate">{{ url }}</span>
            </a>
          </div>
          <HudEmptyState
            v-else
            icon="file-pdf"
            title="Tidak ada brosur PDF"
            hint="Belum ada brosur PDF terdiscover untuk ekspo ini."
          />
        </HudPanel>
      </div>
    </template>
  </div>
</template>
