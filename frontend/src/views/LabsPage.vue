<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import type { Fusion, FusionSuggestion, VendorCandidate } from '@/api/types'
import ConfirmCountdownModal from '@/components/ConfirmCountdownModal.vue'
import LabsFusionResult from '@/components/LabsFusionResult.vue'
import LabsSuggestionCard from '@/components/LabsSuggestionCard.vue'
import LabsVendorCard from '@/components/LabsVendorCard.vue'

/**
 * Labs — Fusion Composer, Bench archetype.
 *
 * Layout intent: split-canvas. LEFT 4-col sticky control rail with the
 * cinema-scale selected count + AI suggest CTA + search + filter + hint
 * + combine button. RIGHT 8-col composer canvas with suggestions, vendor
 * grid, and the live fusion result. No more tab-then-sequential-cards.
 *
 * Real data only: /labs/candidates, /labs/suggestions, /labs/fusions.
 */

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
  } catch {
    toast.error('Gagal ngambil saran AI')
  } finally {
    suggestLoading.value = false
  }
}

function useSuggestion(vendorIds: string[]) {
  selected.value = new Set(vendorIds)
  toast.success(`${vendorIds.length} vendor terpilih dari saran`)
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
const canCombine = computed(() => selected.value.size >= 2)

const deepenBusy = ref<Set<string>>(new Set())

async function deepenVendor(vendorId: string) {
  const next = new Set(deepenBusy.value)
  next.add(vendorId)
  deepenBusy.value = next
  try {
    await api.deepenVendor(vendorId)
    toast.success('Deepen request dikirim. Tunggu beberapa menit, refresh kandidat.')
  } catch {
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
  } catch {
    toast.error('Gagal load detail fusion')
  }
}

watch(activeTab, () => {
  if (activeTab.value === 'history') historyQuery.refetch()
})

const formatNum = (n: number | null | undefined) => {
  if (n === null || n === undefined || !Number.isFinite(n)) return '—'
  return new Intl.NumberFormat('id-ID').format(n)
}
</script>

<template>
  <div class="labs-canvas">
    <!-- ============================================================== -->
    <!-- HERO STRIP — eyebrow + selected-count cinema numeral             -->
    <!-- ============================================================== -->
    <section class="labs-hero">
      <div class="labs-hero__ticker fade-up" style="animation-delay: 0ms">
        <span class="dot dot-amber dot-glow" />
        <span class="atlas-hero__ticker-tag">FUSION COMPOSER</span>
        <span class="atlas-hero__ticker-msg">
          {{ candidates.length }} KANDIDAT AKTIF &middot;
          {{ historyQuery.data.value?.items?.length ?? 0 }} FUSION HISTORIS &middot;
          EKSPERIMEN AI &middot; HASIL TIDAK DETERMINISTIK
        </span>
        <span class="atlas-hero__ticker-stamp">LABS-01</span>
      </div>

      <div class="labs-hero__stencil fade-up" style="animation-delay: 40ms" aria-hidden="true">
        AUTOCRAWL &middot; LABS &middot; FUSION COMPOSER &middot; EKSPERIMENTAL STUDIO
      </div>

      <div class="labs-hero__body fade-up" style="animation-delay: 100ms">
        <div class="labs-hero__copy">
          <span class="eyebrow eyebrow-accent">// 01 LABS</span>
          <h1 class="display-hero mt-4">
            Vendor <span class="text-amber">Fusion</span>.
          </h1>
          <p class="text-ink-2 mt-3 max-w-xl">
            Pilih dua atau lebih kandidat vendor, beri petunjuk produk, AI komposit jadi
            satu nama dagang baru dengan draft email outreach. Eksperimen, jangan didewakan.
          </p>
        </div>

        <!-- Tabs as pills, right-aligned -->
        <div class="labs-hero__tabs">
          <button
            type="button"
            class="labs-tab"
            :class="{ 'labs-tab--active': activeTab === 'create' }"
            @click="activeTab = 'create'"
          >
            Bikin Baru
            <span class="num labs-tab__num">{{ selected.size }}</span>
          </button>
          <button
            type="button"
            class="labs-tab"
            :class="{ 'labs-tab--active': activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            Riwayat
            <span class="num labs-tab__num">{{ historyQuery.data.value?.items?.length ?? 0 }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- BENCH — sticky control rail + composer canvas                    -->
    <!-- ============================================================== -->
    <section v-if="activeTab === 'create'" class="labs-bench">
      <!-- LEFT 4: control rail, sticky -->
      <aside class="labs-rail">
        <div class="bezel bezel-lg">
          <div class="bezel-core p-6 flex flex-col gap-5">
            <!-- Cinema selected count -->
            <div>
              <span class="eyebrow">// TERPILIH</span>
              <div class="labs-rail__num num">
                {{ selected.size === 0 ? '00' : formatNum(selected.size) }}
              </div>
              <span class="text-ink-mute text-xs">vendor di mejakerja</span>
            </div>

            <!-- AI suggestion CTA -->
            <button
              class="btn btn-amber btn-lg w-full justify-between"
              type="button"
              :disabled="suggestLoading"
              @click="fetchSuggestions"
            >
              <span>{{ suggestLoading ? 'Mencari Saran…' : 'Cari Saran AI' }}</span>
              <span class="btn-icon-nest">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M7 2v3M7 9v3M2 7h3M9 7h3M3.5 3.5l2 2M8.5 8.5l2 2M3.5 10.5l2-2M8.5 5.5l2-2" />
                </svg>
              </span>
            </button>

            <!-- Search + filter -->
            <div class="space-y-3">
              <span class="eyebrow">// FILTER KANDIDAT</span>
              <input
                v-model="search"
                type="text"
                placeholder="Cari nama vendor"
                class="input"
              >
              <label class="flex items-center gap-2 cursor-pointer text-sm text-ink-2">
                <input v-model="onlyWithEmail" type="checkbox" class="h-4 w-4 cursor-pointer accent-amber">
                <span>Hanya yang punya email tervalidasi</span>
              </label>
            </div>

            <!-- Hint + combine -->
            <div class="space-y-3 pt-3 rule-t">
              <span class="eyebrow">// PETUNJUK COMBINE</span>
              <input
                v-model="hint"
                type="text"
                placeholder="Contoh: layanan B2B sektor pertahanan"
                class="input"
              >
              <span v-if="missingEmail.length" class="pill pill-warn">
                {{ missingEmail.length }} tanpa email
              </span>

              <button
                class="btn btn-amber btn-lg w-full justify-between"
                type="button"
                :disabled="!canCombine || combineLoading"
                @click="openCombine"
              >
                <span>{{ combineLoading ? 'Generating…' : 'Combine ' + selected.size }}</span>
                <span class="btn-icon-nest">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M3 7h8M7 3l4 4-4 4" />
                  </svg>
                </span>
              </button>
              <button
                v-if="selected.size > 0"
                class="btn btn-ghost btn-sm w-full"
                type="button"
                @click="selected = new Set()"
              >
                <span>Bersihkan Pilihan</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- RIGHT 8: composer canvas -->
      <div class="labs-canvas-right">
        <!-- Fusion result spotlight when present -->
        <div v-if="lastFusion" class="labs-spotlight">
          <div class="bezel bezel-lg">
            <div class="bezel-core p-6">
              <div class="flex items-center justify-between mb-4">
                <span class="eyebrow eyebrow-accent">
                  <span class="live-dot" />
                  HASIL FUSION BARU
                </span>
                <span class="num text-ink" style="font-size: 14px; font-weight: 600">
                  {{ lastFusion.name }}
                </span>
              </div>
              <LabsFusionResult :fusion="lastFusion" />
            </div>
          </div>
        </div>

        <!-- Suggestions row -->
        <div v-if="suggestions.length > 0" class="labs-suggestions">
          <div class="flex items-center justify-between mb-3 px-2">
            <span class="eyebrow">// SARAN AI</span>
            <span class="text-ink-mute text-xs num">{{ suggestions.length }} saran</span>
          </div>
          <div class="grid grid-cols-1 gap-3 xl:grid-cols-2 2xl:grid-cols-3">
            <LabsSuggestionCard
              v-for="(s, idx) in suggestions"
              :key="idx"
              :suggestion="s"
              :vendor-map="candidateMap"
              @use-suggestion="useSuggestion"
            />
          </div>
        </div>

        <!-- Vendor candidate grid -->
        <div class="labs-grid">
          <div class="flex items-center justify-between mb-3 px-2">
            <span class="eyebrow">// KANDIDAT VENDOR &middot; {{ candidates.length }}</span>
            <span class="num text-ink-mute text-xs">limit 100</span>
          </div>
          <div v-if="candidatesQuery.isLoading.value" class="py-16 text-center">
            <span class="dot dot-amber pulse-soft mx-auto inline-block" />
            <p class="label label-mute mt-3">Memuat kandidat…</p>
          </div>
          <div v-else-if="candidates.length === 0" class="py-16 text-center">
            <span class="text-ink-mute" style="font-size: 48px">∅</span>
            <p class="label label-mute mt-3">Belum ada kandidat</p>
            <p class="text-xs text-ink-mute mt-1">Matikan filter "Punya email" atau enrich vendor dulu</p>
          </div>
          <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
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
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- HISTORY tab                                                      -->
    <!-- ============================================================== -->
    <section v-else class="labs-history">
      <article v-if="historyDetail" class="bezel bezel-lg">
        <div class="bezel-core p-6">
          <div class="flex items-center justify-between mb-4">
            <span class="eyebrow eyebrow-accent">// DETAIL FUSION</span>
            <button class="btn btn-ghost btn-sm" type="button" @click="historyDetail = null">
              <span>Tutup</span>
            </button>
          </div>
          <LabsFusionResult :fusion="historyDetail" />
        </div>
      </article>

      <article v-else class="labs-history__list">
        <div class="flex items-center justify-between mb-4 px-2">
          <span class="eyebrow">// SEMUA FUSION HISTORIS</span>
          <span class="num text-ink-mute text-xs">
            {{ historyQuery.data.value?.items?.length ?? 0 }} record
          </span>
        </div>
        <div v-if="historyQuery.isLoading.value" class="py-16 text-center">
          <span class="dot dot-amber pulse-soft mx-auto inline-block" />
          <p class="label label-mute mt-3">Memuat…</p>
        </div>
        <div v-else-if="(historyQuery.data.value?.items?.length ?? 0) === 0" class="py-16 text-center">
          <span class="text-ink-mute" style="font-size: 48px">∅</span>
          <p class="label label-mute mt-3">Belum ada fusion</p>
          <p class="text-xs text-ink-mute mt-1">Bikin yang pertama di tab Bikin Baru</p>
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
      </article>
    </section>

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

<style scoped>
.labs-canvas { position: relative; min-height: 100dvh; }

/* HERO */
.labs-hero {
  position: relative;
  padding: 12px 28px 32px;
  border-bottom: 1px solid rgb(var(--rule) / var(--rule-alpha));
  overflow: hidden;
}
.labs-hero::before {
  content: '';
  position: absolute;
  inset: -10%;
  z-index: 0;
  background-image: var(--aurora-1), var(--aurora-2), var(--aurora-3);
  background-repeat: no-repeat;
  opacity: 0.55;
  pointer-events: none;
  animation: aurora-drift 22s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.labs-hero > * { position: relative; z-index: 1; }

.labs-hero__ticker {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 8px;
  font-family: 'Geist Variable', 'Geist', ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgb(var(--ink-2));
}
.labs-hero__ticker .atlas-hero__ticker-tag { color: rgb(var(--accent)); font-weight: 600; }
.labs-hero__ticker .atlas-hero__ticker-msg {
  flex: 1;
  color: rgb(var(--ink));
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.labs-hero__ticker .atlas-hero__ticker-stamp { color: rgb(var(--ink-mute)); }

.labs-hero__stencil {
  position: absolute;
  left: -10px;
  top: 50%;
  z-index: 2;
  transform: rotate(-90deg);
  transform-origin: left center;
  white-space: nowrap;
  font-family: 'Geist Variable', 'Geist', ui-monospace, monospace;
  font-weight: 500;
  font-size: 10.5px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: rgb(var(--ink-mute) / 0.6);
  pointer-events: none;
}

.labs-hero__body {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 32px;
  padding: 8px 8px 0;
  flex-wrap: wrap;
}
.labs-hero__copy { max-width: 720px; }

.labs-hero__tabs {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.labs-tab {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  border-radius: 9999px;
  border: 1px solid rgb(var(--rule) / var(--rule-strong-alpha));
  background: rgb(var(--surface));
  font-family: 'Geist Variable', 'Geist', sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: rgb(var(--ink-2));
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: all var(--dur-240) var(--ease-out);
}
.labs-tab:hover { transform: translateY(-1px); box-shadow: var(--shadow-card-hover); }
.labs-tab--active {
  background: rgb(var(--ink));
  border-color: rgb(var(--ink));
  color: rgb(var(--surface));
}
.labs-tab__num {
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 9999px;
  background: rgb(var(--ink) / 0.08);
  color: inherit;
  font-weight: 600;
}
.labs-tab--active .labs-tab__num { background: rgb(var(--surface) / 0.16); }

/* BENCH */
.labs-bench {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
  padding: 24px 28px 56px;
  align-items: start;
}
.labs-rail { position: sticky; top: 12px; }
.labs-rail__num {
  font-family: 'Geist Variable', 'Geist', sans-serif;
  font-weight: 700;
  font-size: clamp(3rem, 6vw, 5rem);
  line-height: 1.0;
  letter-spacing: -0.06em;
  padding-block: 0.04em;
  margin-top: 6px;
  background: linear-gradient(
    180deg,
    rgb(var(--accent-hot)) 0%,
    rgb(var(--accent)) 55%,
    rgb(var(--accent-glow, var(--accent))) 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-variant-numeric: tabular-nums;
}

.labs-canvas-right {
  display: flex;
  flex-direction: column;
  gap: 32px;
  min-width: 0;
}
.labs-spotlight { min-width: 0; }
.labs-suggestions { min-width: 0; }
.labs-grid { min-width: 0; }

/* HISTORY */
.labs-history { padding: 24px 28px 56px; }
.labs-history__list { padding: 8px 0; }

@media (max-width: 1100px) {
  .labs-hero { padding: 8px 16px 24px; }
  .labs-hero__stencil { display: none; }
  .labs-hero__body { flex-direction: column; align-items: flex-start; }
  .labs-hero__tabs { width: 100%; }
  .labs-bench {
    grid-template-columns: 1fr;
    padding: 16px 16px 36px;
  }
  .labs-rail { position: static; }
  .labs-history { padding: 16px 16px 36px; }
}
</style>
