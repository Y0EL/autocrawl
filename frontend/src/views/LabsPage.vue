<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import type { Fusion, FusionSuggestion, VendorCandidate } from '@/api/types'
import ConfirmCountdownModal from '@/components/ConfirmCountdownModal.vue'
import HudPanel from '@/components/HudPanel.vue'
import LabsFusionResult from '@/components/LabsFusionResult.vue'
import LabsSuggestionCard from '@/components/LabsSuggestionCard.vue'
import LabsVendorCard from '@/components/LabsVendorCard.vue'

type Tab = 'create' | 'history'
const activeTab = ref<Tab>('create')

const search = ref('')
const onlyWithEmail = ref(false)
const selected = ref<Set<string>>(new Set())
const hint = ref('')
const showConfirm = ref(false)

const candidatesQuery = useQuery({
  queryKey: ['labs-candidates', search, onlyWithEmail],
  queryFn: () => api.labs.candidates({
    search: search.value || undefined,
    only_with_email: onlyWithEmail.value,
    limit: 100,
  }),
})

const candidates = computed<VendorCandidate[]>(() => candidatesQuery.data.value?.items ?? [])
const candidateMap = computed(() => {
  const m = new Map<string, VendorCandidate>()
  for (const v of candidates.value) m.set(v.vendor_id, v)
  return m
})

const suggestions = ref<FusionSuggestion[]>([])
const suggestLoading = ref(false)

async function fetchSuggestions() {
  suggestLoading.value = true
  try {
    const res = await api.labs.suggest({})
    suggestions.value = res.suggestions
    if (res.suggestions.length === 0) {
      toast.info('Belum ada saran yang masuk akal. Coba lagi atau periksa data vendor.')
    }
  } catch (e) {
    toast.error('Gagal ngambil saran AI')
  } finally {
    suggestLoading.value = false
  }
}

function useSuggestion(vendorIds: string[]) {
  selected.value = new Set(vendorIds)
  toast.success(`${vendorIds.length} vendor terpilih dari saran`)
  if (typeof window !== 'undefined') {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }
}

function toggleVendor(vendorId: string) {
  const next = new Set(selected.value)
  if (next.has(vendorId)) next.delete(vendorId)
  else next.add(vendorId)
  selected.value = next
}

const selectedVendors = computed(() =>
  Array.from(selected.value)
    .map((id) => candidateMap.value.get(id))
    .filter((v): v is VendorCandidate => Boolean(v)),
)

const missingEmail = computed(() => selectedVendors.value.filter((v) => !v.has_verified_email))
// Email no longer gates Combine — operator can fuse vendors without
// verified email. `missingEmail` still computed so the UI can warn,
// but it doesn't block.
const canCombine = computed(() => selected.value.size >= 2)

const deepenBusy = ref<Set<string>>(new Set())

async function deepenVendor(vendorId: string) {
  const next = new Set(deepenBusy.value)
  next.add(vendorId)
  deepenBusy.value = next
  try {
    await api.deepenVendor(vendorId)
    toast.success('Deepen request dikirim. Tunggu beberapa menit, refresh kandidat.')
  } catch (e) {
    toast.error('Gagal trigger deepen')
  } finally {
    const after = new Set(deepenBusy.value)
    after.delete(vendorId)
    deepenBusy.value = after
  }
}

const combineLoading = ref(false)
const lastFusion = ref<Fusion | null>(null)

function openCombine() {
  if (!canCombine.value) return
  showConfirm.value = true
}

async function doCombine() {
  combineLoading.value = true
  lastFusion.value = null
  try {
    const fusion = await api.labs.create({
      vendor_ids: Array.from(selected.value),
      hint: hint.value || undefined,
    })
    lastFusion.value = fusion
    toast.success(`Fusion "${fusion.name}" berhasil dibikin`)
    selected.value = new Set()
    hint.value = ''
    historyQuery.refetch()
  } catch (e) {
    let msg = 'Combine gagal'
    if (axios.isAxiosError(e) && e.response?.data) {
      const detail = e.response.data.detail
      if (typeof detail === 'string') msg = detail
      else if (detail?.hint) msg = detail.hint
    }
    toast.error(msg)
  } finally {
    combineLoading.value = false
  }
}

const historyQuery = useQuery({
  queryKey: ['labs-history'],
  queryFn: () => api.labs.list({ limit: 50 }),
})

const historyDetail = ref<Fusion | null>(null)

async function openHistoryDetail(fusionId: string) {
  try {
    historyDetail.value = await api.labs.detail(fusionId)
  } catch (e) {
    toast.error('Gagal load detail fusion')
  }
}

watch(activeTab, () => {
  if (activeTab.value === 'history') historyQuery.refetch()
})
</script>

<template>
  <div class="space-y-4 p-4">
    <HudPanel code="LABS" accent>
      <template #default>
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="font-mono text-2xl font-semibold text-base-900 dark:text-base-50">
            Labs
          </h1>
          <span class="hud-pill hud-pill-warn">
            EXPERIMENTAL
          </span>
        </div>
        <p class="mt-2 font-mono text-sm text-base-600 dark:text-base-300">
          Eksperimen kombinasi vendor jadi produk baru. Hasilnya AI generate dan bisa salah,
          terus eksperimen sampai dapat ide yang menarik.
        </p>
      </template>
    </HudPanel>

    <div class="flex gap-1 border-b border-base-200 dark:border-base-700">
      <button
        type="button"
        :class="[
          'px-4 py-2 font-mono text-2xs uppercase tracking-ops transition-colors',
          activeTab === 'create'
            ? 'border-b-2 border-accent-500 text-accent-700 dark:text-accent-400'
            : 'text-base-500 hover:text-base-800 dark:text-base-400 dark:hover:text-base-100',
        ]"
        @click="activeTab = 'create'"
      >
        Bikin Baru
      </button>
      <button
        type="button"
        :class="[
          'px-4 py-2 font-mono text-2xs uppercase tracking-ops transition-colors',
          activeTab === 'history'
            ? 'border-b-2 border-accent-500 text-accent-700 dark:text-accent-400'
            : 'text-base-500 hover:text-base-800 dark:text-base-400 dark:hover:text-base-100',
        ]"
        @click="activeTab = 'history'"
      >
        Riwayat
      </button>
    </div>

    <div v-if="activeTab === 'create'" class="space-y-4">
      <HudPanel title="Saran AI" code="01">
        <template #actions>
          <button
            class="hud-btn hud-btn-primary"
            type="button"
            :disabled="suggestLoading"
            @click="fetchSuggestions"
          >
            {{ suggestLoading ? 'Generating..' : 'Cari Saran AI' }}
          </button>
        </template>
        <div v-if="suggestions.length === 0" class="font-mono text-2xs text-base-500 dark:text-base-400">
          Klik tombol di atas buat dapet 3-5 saran combo dari AI berdasarkan kandidat vendor punya email tervalidasi.
        </div>
        <div v-else class="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
          <LabsSuggestionCard
            v-for="(s, idx) in suggestions"
            :key="idx"
            :suggestion="s"
            :vendor-map="candidateMap"
            @use-suggestion="useSuggestion"
          />
        </div>
      </HudPanel>

      <HudPanel title="Kandidat Vendor" code="02">
        <template #actions>
          <input
            v-model="search"
            type="text"
            placeholder="cari nama vendor"
            class="hud-input w-48"
          >
          <label class="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">
            <input v-model="onlyWithEmail" type="checkbox" class="accent-accent-500">
            Punya email
          </label>
        </template>
        <div v-if="candidatesQuery.isLoading.value" class="font-mono text-2xs text-base-500 dark:text-base-400">
          Memuat..
        </div>
        <div v-else-if="candidates.length === 0" class="font-mono text-2xs text-base-500 dark:text-base-400">
          Belum ada kandidat. Coba matiin filter "Punya email" atau enrich vendor dulu.
        </div>
        <div v-else class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <LabsVendorCard
            v-for="v in candidates"
            :key="v.vendor_id"
            :vendor="v"
            :selected="selected.has(v.vendor_id)"
            :busy-deepen="deepenBusy.has(v.vendor_id)"
            @toggle="toggleVendor"
            @deepen="deepenVendor"
          />
        </div>
      </HudPanel>

      <HudPanel v-if="lastFusion" title="Hasil Fusion Baru" code="!!">
        <LabsFusionResult :fusion="lastFusion" />
      </HudPanel>
    </div>

    <div v-else class="space-y-4">
      <HudPanel v-if="historyDetail" title="Detail Fusion" code="DET">
        <template #actions>
          <button class="hud-btn hud-btn-ghost" type="button" @click="historyDetail = null">
            Tutup
          </button>
        </template>
        <LabsFusionResult :fusion="historyDetail" />
      </HudPanel>

      <HudPanel v-else title="Riwayat Fusion" code="HIS">
        <div v-if="historyQuery.isLoading.value" class="font-mono text-2xs text-base-500 dark:text-base-400">
          Memuat..
        </div>
        <div v-else-if="(historyQuery.data.value?.items?.length ?? 0) === 0" class="font-mono text-2xs text-base-500 dark:text-base-400">
          Belum ada fusion. Bikin yang pertama di tab Bikin Baru.
        </div>
        <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <LabsFusionResult
            v-for="f in historyQuery.data.value?.items ?? []"
            :key="f.fusion_id"
            :fusion="(f as unknown as Fusion)"
            compact
            @open-detail="openHistoryDetail"
          />
        </div>
      </HudPanel>
    </div>

    <div
      v-if="activeTab === 'create' && selected.size > 0"
      class="sticky bottom-4 z-30"
    >
      <div class="hud-panel border-accent-500 shadow-hud-strong">
        <div class="hud-panel-body flex flex-wrap items-center gap-3">
          <div class="flex flex-1 items-center gap-3">
            <span class="font-mono text-sm text-base-900 dark:text-base-50">
              {{ selected.size }} vendor terpilih
            </span>
            <span v-if="missingEmail.length" class="hud-pill hud-pill-warn">
              {{ missingEmail.length }} TANPA EMAIL
            </span>
          </div>
          <input
            v-model="hint"
            type="text"
            placeholder="hint produk (opsional)"
            class="hud-input w-64"
          >
          <button class="hud-btn hud-btn-ghost" type="button" @click="selected = new Set()">
            Bersihin
          </button>
          <button
            class="hud-btn hud-btn-primary"
            type="button"
            :disabled="!canCombine || combineLoading"
            @click="openCombine"
          >
            {{ combineLoading ? 'Generating..' : 'Combine' }}
          </button>
        </div>
      </div>
    </div>

    <ConfirmCountdownModal
      v-model:open="showConfirm"
      title="Yakin mau combine?"
      :body="'Ini eksperimen, hasilnya bisa ga sesuai ekspektasi. AI bisa salah saran produk dan email draft.\nLo bertanggung jawab review hasilnya sebelum kirim email beneran ke vendor.\n\nLanjut?'"
      :countdown="3"
      confirm-label="Setuju, Combine"
      cancel-label="Batal"
      tone="danger"
      @confirm="doCombine"
    />
  </div>
</template>
