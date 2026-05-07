<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { useTheme } from '@/composables/useTheme'
import { api } from '@/api/client'

/**
 * Editorial topbar — masthead + omnisearch + clock + ENGAGE.
 *
 * The masthead reads "MAP / GLOBAL EXHIBITOR" with a vermilion drop-cap on
 * the M; the search field carries a ⌘K affordance; the right cluster shows
 * a live clock with a blinking colon and the run-control button.
 */

const queryClient = useQueryClient()
const { isDark, toggleDark } = useTheme()

const search = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

const now = ref(new Date())
let tickHandle = 0
onMounted(() => {
  tickHandle = window.setInterval(() => { now.value = new Date() }, 1000)
})
onBeforeUnmount(() => {
  if (tickHandle) window.clearInterval(tickHandle)
})

const clockHM = computed(() => {
  const h = String(now.value.getHours()).padStart(2, '0')
  const m = String(now.value.getMinutes()).padStart(2, '0')
  return { h, m }
})
const tzLabel = computed(() => {
  try {
    return new Intl.DateTimeFormat(undefined, { timeZoneName: 'short' })
      .formatToParts(now.value)
      .find((p) => p.type === 'timeZoneName')?.value ?? ''
  } catch {
    return ''
  }
})

const activeQuery = useQuery({
  queryKey: ['runs', 'active'],
  queryFn: api.activeRun,
  refetchInterval: 5000,
})
const isRunning = computed(() => Boolean(activeQuery.data.value?.active))
const stopRequested = computed(() => {
  const a = activeQuery.data.value?.active as { stop_requested?: boolean } | null | undefined
  return Boolean(a?.stop_requested)
})

const submitting = ref(false)
const showModeMenu = ref(false)

async function trigger(mode: 'dev' | 'normal' | 'aggressive' = 'normal') {
  showModeMenu.value = false
  if (isRunning.value || submitting.value) return
  submitting.value = true
  try {
    await api.triggerRun(mode)
    toast.success('Operasi diluncurkan', { description: `Mode ${mode.toUpperCase()} berjalan di background.` })
    ;['runs','vendors','expos','pdfs','overview','stats','exhibitor-refs'].forEach((k) =>
      queryClient.invalidateQueries({ queryKey: [k] }),
    )
  } catch (err: unknown) {
    const e = err as { response?: { status?: number } }
    if (e.response?.status === 409) toast.warning('Operasi masih aktif')
    else toast.error('Gagal meluncurkan operasi')
  } finally {
    submitting.value = false
  }
}

function focusSearch() { searchInput.value?.focus() }
function onKeyDown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault(); focusSearch()
  }
}
onMounted(() => { window.addEventListener('keydown', onKeyDown) })
onBeforeUnmount(() => { window.removeEventListener('keydown', onKeyDown) })
</script>

<template>
  <header class="atlas-topbar rule-b bg-paper relative z-50 flex h-16 shrink-0 items-stretch">
    <!-- Masthead -->
    <div class="rule-r flex w-[208px] items-end px-5 pb-3 -ml-px">
      <div class="flex flex-col leading-none">
        <span class="display text-[1.375rem] font-semibold tracking-tight">
          <span class="text-vermilion">A</span>utocrawl<span class="text-ink-mute"></span>
        </span>
      </div>
    </div>

    <!-- Search -->
    <div class="flex flex-1 items-center px-6">
      <div class="flex w-full max-w-3xl items-center gap-3">
        <Icon name="search" :size="16" class="text-ink-mute" />
        <input
          ref="searchInput"
          v-model="search"
          type="text"
          placeholder="Cari vendor, ekspo, negara, atau brosur…"
          class="flex-1 bg-transparent border-0 outline-none text-[0.9375rem] placeholder:text-ink-mute font-sans"
          autocomplete="off"
          spellcheck="false"
        />
        <kbd class="font-mono text-[0.625rem] tracking-widest border border-rule px-1.5 py-0.5 text-ink-mute">⌘K</kbd>
      </div>
    </div>

    <!-- Right cluster -->
    <div class="flex items-stretch">
      <!-- Live clock -->
      <div class="rule-l flex items-center px-5 gap-3">
        <span class="dot dot-vermilion ink-blink"></span>
        <div class="flex items-baseline gap-1">
          <span class="num-display text-[1.25rem]">{{ clockHM.h }}</span>
          <span class="num-display text-[1.25rem] text-ink-mute ink-blink">:</span>
          <span class="num-display text-[1.25rem]">{{ clockHM.m }}</span>
        </div>
        <span class="label">{{ tzLabel }}</span>
      </div>

      <!-- Engage button + mode menu -->
      <div class="rule-l flex items-center px-4 relative">
        <button
          class="btn btn-accent h-9"
          :disabled="isRunning || submitting"
          @click="trigger('normal')"
        >
          <Icon
            :name="submitting ? 'loader' : (isRunning ? 'radio' : 'play')"
            :size="14"
            :class="submitting ? 'animate-spin' : ''"
          />
          <span>{{ isRunning ? (stopRequested ? 'STOP…' : 'BERJALAN') : 'ENGAGE' }}</span>
        </button>
        <button
          class="btn btn-accent h-9 -ml-px"
          :disabled="isRunning || submitting"
          aria-label="Pilih mode"
          @click="showModeMenu = !showModeMenu"
        >
          <Icon name="chevron-down" :size="12" />
        </button>
        <Transition
          enter-active-class="transition duration-150"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-100"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="showModeMenu"
            class="absolute right-4 top-[3.6rem] z-[55] w-56 bg-paper rule shadow-[0_8px_28px_rgb(0_0_0/0.08)]"
          >
            <button
              class="flex w-full items-center justify-between px-4 py-2.5 text-left rule-b hover:bg-paper-2"
              @click="trigger('dev')"
            >
              <span class="font-mono text-[0.75rem] uppercase tracking-[0.14em]">Dev</span>
              <span class="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-mute">SAMPEL KECIL</span>
            </button>
            <button
              class="flex w-full items-center justify-between px-4 py-2.5 text-left rule-b hover:bg-paper-2"
              @click="trigger('normal')"
            >
              <span class="font-mono text-[0.75rem] uppercase tracking-[0.14em]">Normal</span>
              <span class="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-mute">DEFAULT</span>
            </button>
            <button
              class="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-paper-2"
              @click="trigger('aggressive')"
            >
              <span class="font-mono text-[0.75rem] uppercase tracking-[0.14em]">Agresif</span>
              <span class="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-mute">FULL THROTTLE</span>
            </button>
          </div>
        </Transition>
      </div>

      <!-- Theme toggle -->
      <button
        class="rule-l flex w-12 items-center justify-center hover:bg-paper-2"
        :title="isDark ? 'Mode terang' : 'Mode gelap'"
        @click="toggleDark()"
      >
        <Icon :name="isDark ? 'sun' : 'moon'" :size="16" class="text-ink-2" />
      </button>
    </div>
  </header>
</template>

<style scoped>
/* Children pick up their own feature-settings from .font-mono / .display
 * / .num-display utility classes — no need to set anything at the wrapper. */
</style>
