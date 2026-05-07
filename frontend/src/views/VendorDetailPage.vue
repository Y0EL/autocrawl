<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import HudPanel from '@/components/HudPanel.vue'
import HudIndustryBadge from '@/components/HudIndustryBadge.vue'
import HudCompletenessBar from '@/components/HudCompletenessBar.vue'
import HudProvenanceTimeline from '@/components/HudProvenanceTimeline.vue'
import HudStatusPill from '@/components/HudStatusPill.vue'
import HudEmptyState from '@/components/HudEmptyState.vue'

const props = defineProps<{ domain: string }>()
const queryClient = useQueryClient()
const deepening = ref(false)

const { data, isLoading, isError } = useQuery({
  queryKey: ['vendor', () => props.domain],
  queryFn: () => api.vendor(props.domain),
  refetchInterval: () => (deepening.value ? 4000 : false),
})

async function deepenVendor() {
  if (!data.value || deepening.value) return
  const target = data.value.vendor_id || data.value.domain
  if (!target) return
  deepening.value = true
  toast.info('Perdalam vendor diluncurkan', {
    description: 'AI re-enrich sedang berjalan. Skor akan update otomatis dalam beberapa detik.',
  })
  try {
    await api.deepenVendor(target)
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['vendor', () => props.domain] })
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
    }, 6000)
    setTimeout(() => {
      deepening.value = false
      queryClient.invalidateQueries({ queryKey: ['vendor', () => props.domain] })
    }, 30000)
  } catch {
    deepening.value = false
    toast.error('Gagal meluncurkan deepen', {
      description: 'Cek log API container.',
    })
  }
}

const initials = computed(() => data.value?.company_name?.charAt(0).toUpperCase() ?? '?')

const showOriginal = ref(false)
const isTranslated = computed(
  () => data.value?.language_code === 'id' && Boolean(data.value?.translation_method),
)

const displayDescription = computed(() =>
  showOriginal.value && data.value?.description_original
    ? data.value.description_original
    : data.value?.description ?? null,
)
const displayTagline = computed(() =>
  showOriginal.value && data.value?.tagline_original
    ? data.value.tagline_original
    : data.value?.tagline ?? null,
)
const displayProducts = computed(() =>
  showOriginal.value && data.value?.products_original?.length
    ? data.value.products_original
    : data.value?.products ?? [],
)
const displayIndustries = computed(() =>
  showOriginal.value && data.value?.industries_original?.length
    ? data.value.industries_original
    : data.value?.industries ?? [],
)

type Tab = 'profil' | 'kontak' | 'sumber' | 'json'
const tab = ref<Tab>('profil')

function formatDate(iso: string | null | undefined) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })
}

const jsonView = computed(() => (data.value ? JSON.stringify(data.value, null, 2) : ''))

function copyJson() {
  if (!jsonView.value) return
  navigator.clipboard.writeText(jsonView.value)
}
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <RouterLink
      to="/vendors"
      class="inline-flex w-fit items-center gap-2 font-mono text-2xs uppercase tracking-ops text-base-500 hover:text-accent-600 dark:text-base-400 dark:hover:text-accent-300"
    >
      <FaIcon :icon="['fas', 'chevron-left']" class="text-2xs" />
      KEMBALI KE DAFTAR VENDOR
    </RouterLink>

    <div v-if="isLoading" class="hud-panel animate-pulse p-8">
      <div class="h-6 w-1/3 bg-base-200 dark:bg-base-700" />
    </div>

    <HudPanel v-else-if="isError" code="ERR" title="Vendor tidak ditemukan">
      <HudEmptyState
        icon="circle-xmark"
        title="Target tidak ditemukan"
        hint="Vendor dengan domain ini belum terkoleksi atau telah dihapus dari database."
      />
    </HudPanel>

    <template v-else-if="data">
      <HudPanel code="VND-PROFILE" :title="data.company_name">
        <template #actions>
          <HudStatusPill
            :tone="isTranslated ? 'accent' : 'muted'"
            :label="showOriginal ? 'EN' : (isTranslated ? 'ID' : 'EN')"
          />
          <button
            v-if="isTranslated"
            class="hud-btn-ghost h-7"
            @click="showOriginal = !showOriginal"
          >
            <FaIcon :icon="['fas', 'language']" class="text-2xs" />
            <span>{{ showOriginal ? 'LIHAT INDONESIA' : 'LIHAT ENGLISH' }}</span>
          </button>
          <button
            class="hud-btn-primary h-7"
            :disabled="deepening"
            @click="deepenVendor"
          >
            <FaIcon
              :icon="['fas', deepening ? 'circle-notch' : 'crosshairs']"
              :class="deepening ? 'animate-spin text-2xs' : 'text-2xs'"
            />
            <span>{{ deepening ? 'MEMPERDALAM...' : 'PERDALAM SEKARANG' }}</span>
          </button>
        </template>

        <div class="flex flex-col gap-4 md:flex-row md:items-start">
          <div
            v-if="!data.logo_url"
            class="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg border border-accent-600 bg-accent-500/10 font-mono text-3xl font-bold text-accent-600 dark:text-accent-300"
          >
            {{ initials }}
          </div>
          <img
            v-else
            :src="data.logo_url"
            :alt="data.company_name"
            class="h-20 w-20 shrink-0 border border-base-200 bg-white object-contain p-1 dark:border-base-700 dark:bg-base-800"
            referrerpolicy="no-referrer"
          />

          <div class="flex flex-1 flex-col gap-3">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-xl font-semibold tracking-tight text-base-900 dark:text-base-50">
                {{ data.company_name }}
              </h2>
              <a
                v-if="data.canonical_url"
                :href="data.canonical_url"
                target="_blank"
                rel="noopener noreferrer"
                class="hud-mono-num text-xs text-accent-600 hover:underline dark:text-accent-300"
              >
                {{ data.domain ?? '-' }}
                <FaIcon :icon="['fas', 'arrow-up-right-from-square']" class="ml-1 text-2xs" />
              </a>
              <span
                v-else
                class="hud-mono-num text-xs text-base-400 dark:text-base-500"
              >
                {{ data.domain ?? 'belum-ter-resolve' }}
              </span>
            </div>

            <p
              v-if="displayTagline"
              class="text-sm font-medium text-base-700 dark:text-base-200"
            >
              {{ displayTagline }}
            </p>
            <p
              v-if="displayDescription"
              class="text-sm leading-relaxed text-base-600 dark:text-base-300"
            >
              {{ displayDescription }}
            </p>

            <div v-if="displayIndustries.length" class="flex flex-wrap gap-1.5">
              <HudIndustryBadge v-for="tag in displayIndustries" :key="tag" :label="tag" />
            </div>

            <div v-if="displayProducts.length" class="flex flex-wrap gap-1.5">
              <span v-for="p in displayProducts" :key="p" class="hud-chip">
                {{ p }}
              </span>
            </div>
          </div>

          <div class="flex w-full shrink-0 flex-col gap-2 md:w-56">
            <span class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">
              SKOR KELENGKAPAN
            </span>
            <HudCompletenessBar :score="data.confidence_score" show-label />
            <span class="font-mono text-2xs uppercase tracking-ops text-base-500 dark:text-base-400">
              ENRICHED
            </span>
            <span class="hud-mono-num text-xs text-base-700 dark:text-base-200">
              {{ formatDate(data.last_enriched_at) }}
            </span>
          </div>
        </div>
      </HudPanel>

      <div class="flex items-center gap-1 border-b border-base-200 dark:border-base-700">
        <button
          class="hud-tab"
          :class="tab === 'profil' ? 'hud-tab-active' : ''"
          @click="tab = 'profil'"
        >
          <FaIcon :icon="['fas', 'shield-halved']" class="mr-1.5 text-2xs" />
          Profil
        </button>
        <button
          class="hud-tab"
          :class="tab === 'kontak' ? 'hud-tab-active' : ''"
          @click="tab = 'kontak'"
        >
          <FaIcon :icon="['fas', 'envelope']" class="mr-1.5 text-2xs" />
          Kontak
        </button>
        <button
          class="hud-tab"
          :class="tab === 'sumber' ? 'hud-tab-active' : ''"
          @click="tab = 'sumber'"
        >
          <FaIcon :icon="['fas', 'circle-nodes']" class="mr-1.5 text-2xs" />
          Provenance
        </button>
        <button
          class="hud-tab"
          :class="tab === 'json' ? 'hud-tab-active' : ''"
          @click="tab = 'json'"
        >
          <FaIcon :icon="['fas', 'code']" class="mr-1.5 text-2xs" />
          Raw JSON
        </button>
      </div>

      <div v-if="tab === 'profil'" class="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <HudPanel title="Domain Info" code="DOM-INFO">
          <dl class="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
            <dt class="font-mono uppercase tracking-ops text-base-500 dark:text-base-400">REGISTRAR</dt>
            <dd class="text-right text-base-800 dark:text-base-100">{{ data.registrar ?? '-' }}</dd>
            <dt class="font-mono uppercase tracking-ops text-base-500 dark:text-base-400">NEGARA</dt>
            <dd class="text-right text-base-800 dark:text-base-100">
              {{ data.registrar_country ?? '-' }}
            </dd>
            <dt class="font-mono uppercase tracking-ops text-base-500 dark:text-base-400">UMUR DOMAIN</dt>
            <dd class="hud-mono-num text-right text-base-800 dark:text-base-100">
              {{ data.domain_age_days != null ? `${data.domain_age_days}d` : '-' }}
            </dd>
            <dt class="font-mono uppercase tracking-ops text-base-500 dark:text-base-400">WAYBACK</dt>
            <dd class="hud-mono-num text-right text-base-800 dark:text-base-100">
              {{ data.first_seen_wayback ?? '-' }}
            </dd>
            <dt class="font-mono uppercase tracking-ops text-base-500 dark:text-base-400">BERDIRI</dt>
            <dd class="hud-mono-num text-right text-base-800 dark:text-base-100">
              {{ data.founded_year ?? '-' }}
            </dd>
          </dl>
        </HudPanel>

        <HudPanel title="Alamat" code="ADDR">
          <div v-if="data.address && (data.address.raw || data.address.street || data.address.city || data.address.region || data.address.country)"
               class="flex flex-col gap-1 text-sm text-base-700 dark:text-base-200">
            <span v-if="data.address.street">{{ data.address.street }}</span>
            <span v-if="data.address.city || data.address.region">
              {{ [data.address.city, data.address.region].filter(Boolean).join(', ') }}
            </span>
            <span v-if="data.address.country" class="font-medium">
              {{ data.address.country }} {{ data.address.postal_code ?? '' }}
            </span>
            <!-- Raw free-text fallback when structured fields are sparse
                 (agentic-enriched vendors emit a single `raw` blob with
                 the full street address). -->
            <span
              v-if="data.address.raw && !data.address.street && !data.address.city && !data.address.region"
              class="whitespace-pre-line"
            >
              {{ data.address.raw }}
            </span>
          </div>
          <p v-else class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
            ALAMAT TIDAK DIKETAHUI
          </p>
        </HudPanel>

        <HudPanel title="Tech Stack" code="TECH">
          <div v-if="data.tech_stack.length" class="flex flex-wrap gap-1.5">
            <span v-for="t in data.tech_stack" :key="t" class="hud-chip">{{ t }}</span>
          </div>
          <p v-else class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
            TIDAK ADA TECH STACK TERDETEKSI
          </p>
        </HudPanel>

        <HudPanel title="Sosial" code="SOCIAL">
          <div class="flex flex-wrap gap-2">
            <a
              v-if="data.socials.linkedin"
              :href="data.socials.linkedin"
              target="_blank"
              rel="noopener noreferrer"
              class="hud-btn-ghost h-7"
            >
              <FaIcon :icon="['fab', 'linkedin']" class="text-2xs" />
              <span>LINKEDIN</span>
            </a>
            <a
              v-if="data.socials.twitter"
              :href="data.socials.twitter"
              target="_blank"
              rel="noopener noreferrer"
              class="hud-btn-ghost h-7"
            >
              <FaIcon :icon="['fab', 'x-twitter']" class="text-2xs" />
              <span>X</span>
            </a>
            <a
              v-if="data.socials.youtube"
              :href="data.socials.youtube"
              target="_blank"
              rel="noopener noreferrer"
              class="hud-btn-ghost h-7"
            >
              <FaIcon :icon="['fab', 'youtube']" class="text-2xs" />
              <span>YOUTUBE</span>
            </a>
            <a
              v-if="data.socials.facebook"
              :href="data.socials.facebook"
              target="_blank"
              rel="noopener noreferrer"
              class="hud-btn-ghost h-7"
            >
              <FaIcon :icon="['fab', 'facebook']" class="text-2xs" />
              <span>FACEBOOK</span>
            </a>
            <a
              v-if="data.socials.github"
              :href="data.socials.github"
              target="_blank"
              rel="noopener noreferrer"
              class="hud-btn-ghost h-7"
            >
              <FaIcon :icon="['fab', 'github']" class="text-2xs" />
              <span>GITHUB</span>
            </a>
            <span
              v-if="!data.socials.linkedin && !data.socials.twitter && !data.socials.youtube && !data.socials.facebook && !data.socials.github"
              class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500"
            >
              TIDAK ADA AKUN TERDETEKSI
            </span>
          </div>
        </HudPanel>

        <HudPanel title="Ekspo Terlihat" code="EXP-SEEN">
          <div v-if="data.expos_seen.length" class="flex flex-col gap-1.5">
            <RouterLink
              v-for="ex in data.expos_seen"
              :key="ex"
              :to="`/expos/${ex}`"
              class="hud-mono-num truncate text-xs text-accent-600 hover:underline dark:text-accent-300"
            >
              {{ ex }}
            </RouterLink>
          </div>
          <p v-else class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
            BELUM TERLIHAT DI EKSPO MANAPUN
          </p>
        </HudPanel>

        <HudPanel
          v-if="data.enrichment_gap.length"
          title="Enrichment Gap"
          code="GAP"
          accent
        >
          <p class="mb-2 font-mono text-2xs uppercase tracking-ops text-warn-600 dark:text-warn-400">
            FIELD INI BUTUH PHASE 2 (PAID TIER)
          </p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="g in data.enrichment_gap"
              :key="g"
              class="hud-pill-warn"
            >
              {{ g }}
            </span>
          </div>
        </HudPanel>
      </div>

      <div v-else-if="tab === 'kontak'" class="grid grid-cols-1 gap-3">
        <HudPanel title="Kontak Terkoleksi" code="CONTACT">
          <div v-if="data.contacts.length" class="flex flex-col gap-2.5">
            <div
              v-for="(c, idx) in data.contacts"
              :key="`${c.type}-${idx}`"
              class="border border-base-200 p-2.5 dark:border-base-700"
            >
              <div class="flex flex-wrap items-center gap-2">
                <FaIcon
                  :icon="['fas', c.type === 'email' ? 'envelope' : 'phone']"
                  class="text-2xs text-base-400 dark:text-base-500"
                />
                <span class="hud-mono-num text-sm text-base-800 dark:text-base-100">
                  {{ c.value }}
                </span>
                <HudStatusPill
                  v-if="c.verified === true"
                  tone="ok"
                  :label="`OK ${Math.round((c.verification_score ?? 0) * 100)}%`"
                />
                <HudStatusPill
                  v-else-if="c.verified === false"
                  tone="crit"
                  label="INVALID"
                />
              </div>
              <div
                v-if="c.verification_signals"
                class="mt-2 flex flex-wrap gap-1 font-mono text-2xs uppercase tracking-ops"
              >
                <span v-if="c.verification_signals.mx_present" class="hud-pill-ok">
                  MX OK
                </span>
                <span v-if="c.verification_signals.disposable" class="hud-pill-crit">
                  DISPOSABLE
                </span>
                <span v-if="c.verification_signals.role_based" class="hud-pill-warn">
                  ROLE
                </span>
                <span v-if="c.verification_signals.domain_matches_vendor" class="hud-pill-info">
                  DOMAIN MATCH
                </span>
              </div>
            </div>
          </div>
          <HudEmptyState
            v-else
            icon="envelope"
            title="Belum ada kontak"
            hint="Belum ada email atau nomor telepon yang berhasil diekstrak dari sumber yang ada."
          />
        </HudPanel>
      </div>

      <div v-else-if="tab === 'sumber'">
        <HudPanel title="Source Trail" code="SRC-TRAIL">
          <HudProvenanceTimeline v-if="data.source_trail.length" :entries="data.source_trail" />
          <HudEmptyState
            v-else
            icon="circle-nodes"
            title="Tidak ada provenance"
            hint="Vendor ini belum punya jejak sumber tercatat."
          />
        </HudPanel>
      </div>

      <div v-else-if="tab === 'json'">
        <HudPanel title="Raw JSON" code="JSON">
          <template #actions>
            <button class="hud-btn-ghost h-7" @click="copyJson">
              <FaIcon :icon="['fas', 'copy']" class="text-2xs" />
              <span>SALIN</span>
            </button>
          </template>
          <pre
            class="max-h-[600px] overflow-auto border border-base-200 bg-base-50 p-3 font-mono text-2xs leading-relaxed text-base-700 dark:border-base-700 dark:bg-base-800 dark:text-base-200"
          >{{ jsonView }}</pre>
        </HudPanel>
      </div>
    </template>
  </div>
</template>
