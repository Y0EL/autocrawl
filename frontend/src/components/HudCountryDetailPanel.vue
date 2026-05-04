<script setup lang="ts">
import { computed, watch } from 'vue'
import { useEventListener } from '@vueuse/core'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { flagEmoji } from '@/data/country_resolver'

interface Props {
  country: string
  cca2: string
  visible: boolean
  totalVendors?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'close'): void }>()

const detailQ = useQuery({
  queryKey: computed(() => ['expo-country-detail', props.country]),
  queryFn: () => api.stats.expoCountryDetail(props.country),
  enabled: computed(() => props.visible && Boolean(props.country)),
  staleTime: 30_000,
})

const detail = computed(() => detailQ.data.value)

const sharePct = computed(() => {
  if (!detail.value || !props.totalVendors) return 0
  return Math.round((detail.value.vendor_count / props.totalVendors) * 100)
})

useEventListener('keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.visible) emit('close')
})

watch(
  () => props.country,
  () => {
    if (props.visible) detailQ.refetch()
  },
)

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="translate-x-full opacity-0"
    enter-to-class="translate-x-0 opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="translate-x-0 opacity-100"
    leave-to-class="translate-x-full opacity-0"
  >
    <aside
      v-if="visible"
      class="absolute right-0 top-0 bottom-0 z-30 flex w-[340px] flex-col border-l border-cyan-400/30 bg-[#0c0e14]/95 shadow-[-8px_0_24px_rgba(57,216,255,0.15)] backdrop-blur-md"
    >
      <header
        class="flex shrink-0 items-start justify-between gap-2 border-b border-cyan-400/20 px-4 py-3"
      >
        <div class="flex items-start gap-2">
          <span class="text-3xl leading-none">{{ flagEmoji(cca2) }}</span>
          <div class="flex flex-col">
            <span class="font-mono text-2xs uppercase tracking-ops text-cyan-300">
              GEO-DETAIL · {{ cca2 }}
            </span>
            <span class="font-mono text-sm font-semibold text-base-100">
              {{ country }}
            </span>
          </div>
        </div>
        <button
          class="hud-btn-ghost h-7 px-2 text-2xs"
          aria-label="Tutup panel"
          @click="emit('close')"
        >
          <FaIcon :icon="['fas', 'xmark']" />
        </button>
      </header>

      <div class="flex flex-col gap-3 overflow-y-auto p-3">
        <div v-if="detailQ.isLoading.value" class="py-6 text-center font-mono text-2xs uppercase tracking-ops text-base-500">
          MEMUAT…
        </div>

        <template v-else-if="detail">
          <div class="grid grid-cols-3 gap-2">
            <div class="border border-cyan-400/30 bg-cyan-500/5 px-2 py-2 text-center">
              <div class="font-mono text-[9px] uppercase tracking-ops text-cyan-400/80">VENDOR</div>
              <div class="hud-mono-num text-xl font-bold text-cyan-300">{{ detail.vendor_count }}</div>
            </div>
            <div class="border border-base-700 bg-base-800/40 px-2 py-2 text-center">
              <div class="font-mono text-[9px] uppercase tracking-ops text-base-400">EKSPO</div>
              <div class="hud-mono-num text-xl font-bold text-base-100">{{ detail.expo_count }}</div>
            </div>
            <div class="border border-base-700 bg-base-800/40 px-2 py-2 text-center">
              <div class="font-mono text-[9px] uppercase tracking-ops text-base-400">SHARE</div>
              <div class="hud-mono-num text-xl font-bold text-base-100">{{ sharePct }}%</div>
            </div>
          </div>

          <section class="flex flex-col gap-1.5">
            <div class="font-mono text-2xs uppercase tracking-ops text-base-500">
              EKSPO TERAKHIR ({{ detail.top_expos.length }})
            </div>
            <div v-if="detail.top_expos.length === 0" class="font-mono text-2xs text-base-500">
              Belum ada ekspo terindeks.
            </div>
            <RouterLink
              v-for="expo in detail.top_expos"
              :key="expo.expo_id"
              :to="`/expos/${expo.expo_id}`"
              class="block border border-base-700 bg-base-800/30 px-2 py-1.5 transition-colors hover:border-cyan-400/40 hover:bg-cyan-500/5"
            >
              <div class="font-mono text-xs font-medium text-base-100 line-clamp-2">
                {{ expo.name }}
              </div>
              <div class="flex items-center justify-between font-mono text-2xs text-base-500">
                <span>{{ expo.location || '—' }}</span>
                <span>{{ fmtDate(expo.start_date) }}</span>
              </div>
            </RouterLink>
          </section>

          <section class="flex flex-col gap-1.5">
            <div class="font-mono text-2xs uppercase tracking-ops text-base-500">
              VENDOR PRIORITAS ({{ detail.top_vendors.length }})
            </div>
            <div v-if="detail.top_vendors.length === 0" class="font-mono text-2xs text-base-500">
              Belum ada vendor enriched.
            </div>
            <RouterLink
              v-for="v in detail.top_vendors"
              :key="v.domain || v.company_name"
              :to="v.domain ? `/vendors/${v.domain}` : '/vendors'"
              class="block border border-base-700 bg-base-800/30 px-2 py-1.5 transition-colors hover:border-cyan-400/40 hover:bg-cyan-500/5"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="min-w-0 flex-1">
                  <div class="truncate font-mono text-xs font-medium text-base-100">
                    {{ v.company_name }}
                  </div>
                  <div class="truncate font-mono text-2xs text-base-500">
                    {{ v.domain || 'unresolved' }}
                  </div>
                </div>
                <span class="hud-mono-num shrink-0 text-2xs text-cyan-300">
                  {{ Math.round(v.confidence_score * 100) }}%
                </span>
              </div>
            </RouterLink>
          </section>
        </template>
      </div>

      <footer class="flex shrink-0 flex-col gap-1.5 border-t border-cyan-400/20 p-3">
        <RouterLink
          :to="{ path: '/expos', query: { country } }"
          class="hud-btn flex h-8 items-center justify-between border-cyan-400/40 bg-cyan-500/5 text-2xs uppercase tracking-ops text-cyan-300 hover:bg-cyan-500/15"
          @click="emit('close')"
        >
          <span>LIHAT SEMUA EKSPO</span>
          <FaIcon :icon="['fas', 'chevron-right']" class="text-2xs" />
        </RouterLink>
        <RouterLink
          :to="{ path: '/vendors', query: { country } }"
          class="hud-btn flex h-8 items-center justify-between border-cyan-400/40 bg-cyan-500/5 text-2xs uppercase tracking-ops text-cyan-300 hover:bg-cyan-500/15"
          @click="emit('close')"
        >
          <span>LIHAT SEMUA VENDOR</span>
          <FaIcon :icon="['fas', 'chevron-right']" class="text-2xs" />
        </RouterLink>
      </footer>
    </aside>
  </Transition>
</template>
