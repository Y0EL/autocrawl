<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import IndustryBadge from '@/components/IndustryBadge.vue'
import ProvenanceTimeline from '@/components/ProvenanceTimeline.vue'
import CompletenessBar from '@/components/CompletenessBar.vue'

const props = defineProps<{ domain: string }>()

const { data, isLoading, isError } = useQuery({
  queryKey: ['vendor', () => props.domain],
  queryFn: () => api.vendor(props.domain),
})

const initials = computed(() => data.value?.company_name?.charAt(0) ?? '?')

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

const formatDate = (iso: string | null | undefined) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })
}
</script>

<template>
  <div>
    <RouterLink
      to="/vendors"
      class="mb-4 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
    >
      <i class="fa-solid fa-arrow-left text-xs"></i>
      Kembali ke daftar vendor
    </RouterLink>

    <div v-if="isLoading" class="card animate-pulse p-8">
      <div class="h-6 w-1/3 rounded bg-zinc-200 dark:bg-zinc-800"></div>
    </div>

    <div v-else-if="isError" class="card p-8 text-center text-rose-500">Vendor tidak ditemukan.</div>

    <div v-else-if="data" class="space-y-6">
      <div class="card flex flex-col gap-4 p-6 sm:flex-row sm:items-start">
        <div
          v-if="!data.logo_url"
          class="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 text-3xl font-bold text-white"
        >
          {{ initials }}
        </div>
        <img
          v-else
          :src="data.logo_url"
          :alt="data.company_name"
          class="h-20 w-20 shrink-0 rounded-xl bg-zinc-100 object-contain p-1 dark:bg-zinc-800"
          referrerpolicy="no-referrer"
        />
        <div class="flex flex-1 flex-col gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-2xl font-bold tracking-tight">{{ data.company_name }}</h2>
            <a
              :href="data.canonical_url"
              target="_blank"
              rel="noopener noreferrer"
              class="font-mono text-sm text-accent-600 hover:underline dark:text-accent-400"
            >
              {{ data.domain }}
              <i class="fa-solid fa-arrow-up-right-from-square ml-1 text-xs"></i>
            </a>
            <span
              v-if="isTranslated"
              class="badge bg-sky-100 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400"
              :title="`Translated by ${data.translation_method}`"
            >
              <i class="fa-solid fa-language"></i>
              {{ showOriginal ? 'EN (asli)' : 'ID' }}
            </span>
            <button
              v-if="isTranslated"
              type="button"
              class="btn-ghost h-7 px-2 text-[11px]"
              @click="showOriginal = !showOriginal"
            >
              <i :class="showOriginal ? 'fa-solid fa-flag' : 'fa-solid fa-globe'"></i>
              {{ showOriginal ? 'Lihat Indonesia' : 'Lihat English' }}
            </button>
          </div>
          <p v-if="displayTagline" class="text-sm font-medium text-zinc-600 dark:text-zinc-400">
            {{ displayTagline }}
          </p>
          <p v-if="displayDescription" class="text-sm text-zinc-700 dark:text-zinc-300">
            {{ displayDescription }}
          </p>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <IndustryBadge v-for="tag in displayIndustries" :key="tag" :tag="tag" />
          </div>
          <div v-if="displayProducts.length" class="mt-1 flex flex-wrap gap-1.5">
            <span
              v-for="p in displayProducts"
              :key="p"
              class="badge bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
            >
              {{ p }}
            </span>
          </div>
        </div>
        <div class="flex w-full shrink-0 flex-col items-end gap-2 sm:w-48">
          <span class="text-xs text-zinc-500 dark:text-zinc-400">Skor kelengkapan</span>
          <CompletenessBar :score="data.confidence_score" show-label />
          <span class="text-xs text-zinc-500 dark:text-zinc-400">
            Terakhir di enrich {{ formatDate(data.last_enriched_at) }}
          </span>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-3">
        <div class="card p-5 lg:col-span-2">
          <h3 class="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            <i class="fa-solid fa-route mr-1"></i> Source Trail
          </h3>
          <ProvenanceTimeline :entries="data.source_trail" />
        </div>

        <div class="space-y-6">
          <div class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-address-book mr-1"></i> Kontak
            </h3>
            <div class="space-y-3">
              <div
                v-for="(c, idx) in data.contacts"
                :key="`${c.type}-${idx}`"
                class="flex flex-col gap-1"
              >
                <div class="flex items-center gap-2 text-sm">
                  <i
                    :class="[
                      c.type === 'email' ? 'fa-regular fa-envelope' : 'fa-solid fa-phone',
                      'w-4 text-zinc-400',
                    ]"
                  ></i>
                  <span class="font-mono text-zinc-700 dark:text-zinc-200">{{ c.value }}</span>
                  <span
                    v-if="c.verified === true"
                    class="badge bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                  >
                    <i class="fa-solid fa-circle-check"></i>
                    {{ Math.round((c.verification_score ?? 0) * 100) }}%
                  </span>
                  <span
                    v-else-if="c.verified === false"
                    class="badge bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400"
                  >
                    <i class="fa-solid fa-circle-xmark"></i>
                    invalid
                  </span>
                </div>
                <div
                  v-if="c.verification_signals"
                  class="ml-6 flex flex-wrap gap-1 text-[10px] text-zinc-500 dark:text-zinc-400"
                >
                  <span
                    v-if="c.verification_signals.mx_present"
                    class="rounded bg-zinc-100 px-1.5 py-0.5 dark:bg-zinc-800"
                  >
                    MX OK
                  </span>
                  <span
                    v-if="c.verification_signals.disposable"
                    class="rounded bg-rose-100 px-1.5 py-0.5 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400"
                  >
                    disposable
                  </span>
                  <span
                    v-if="c.verification_signals.role_based"
                    class="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                  >
                    role
                  </span>
                  <span
                    v-if="c.verification_signals.domain_matches_vendor"
                    class="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                  >
                    domain match
                  </span>
                </div>
              </div>
              <p
                v-if="!data.contacts.length"
                class="text-sm text-zinc-500 dark:text-zinc-400"
              >
                Belum ada kontak terkoleksi.
              </p>
            </div>
          </div>

          <div class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-location-dot mr-1"></i> Alamat
            </h3>
            <div v-if="data.address" class="space-y-1 text-sm">
              <p v-if="data.address.street">{{ data.address.street }}</p>
              <p v-if="data.address.city || data.address.region">
                {{ [data.address.city, data.address.region].filter(Boolean).join(', ') }}
              </p>
              <p class="font-medium" v-if="data.address.country">
                {{ data.address.country }} {{ data.address.postal_code ?? '' }}
              </p>
            </div>
            <p v-else class="text-sm text-zinc-500 dark:text-zinc-400">Tidak diketahui.</p>
          </div>

          <div class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-share-nodes mr-1"></i> Sosial
            </h3>
            <div class="flex flex-wrap gap-2">
              <a
                v-if="data.socials.linkedin"
                :href="data.socials.linkedin"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-ghost h-8 px-3 text-xs"
              >
                <i class="fa-brands fa-linkedin"></i> LinkedIn
              </a>
              <a
                v-if="data.socials.twitter"
                :href="data.socials.twitter"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-ghost h-8 px-3 text-xs"
              >
                <i class="fa-brands fa-x-twitter"></i> Twitter
              </a>
              <a
                v-if="data.socials.youtube"
                :href="data.socials.youtube"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-ghost h-8 px-3 text-xs"
              >
                <i class="fa-brands fa-youtube"></i> YouTube
              </a>
              <a
                v-if="data.socials.facebook"
                :href="data.socials.facebook"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-ghost h-8 px-3 text-xs"
              >
                <i class="fa-brands fa-facebook"></i> Facebook
              </a>
              <span
                v-if="!data.socials.linkedin && !data.socials.twitter && !data.socials.youtube && !data.socials.facebook"
                class="text-sm text-zinc-500 dark:text-zinc-400"
              >
                Tidak ada akun terdeteksi.
              </span>
            </div>
          </div>

          <div class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-id-card mr-1"></i> Domain Info
            </h3>
            <dl class="space-y-2 text-sm">
              <div class="flex justify-between">
                <dt class="text-zinc-500 dark:text-zinc-400">Registrar</dt>
                <dd class="text-right">{{ data.registrar ?? '-' }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-zinc-500 dark:text-zinc-400">Country</dt>
                <dd class="text-right">{{ data.registrar_country ?? '-' }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-zinc-500 dark:text-zinc-400">Umur domain</dt>
                <dd class="text-right tabular-nums">
                  {{ data.domain_age_days != null ? `${data.domain_age_days} hari` : '-' }}
                </dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-zinc-500 dark:text-zinc-400">Wayback awal</dt>
                <dd class="text-right">{{ data.first_seen_wayback ?? '-' }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-zinc-500 dark:text-zinc-400">Tahun berdiri</dt>
                <dd class="text-right">{{ data.founded_year ?? '-' }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="data.tech_stack.length" class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-microchip mr-1"></i> Tech Stack
            </h3>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="t in data.tech_stack"
                :key="t"
                class="badge bg-zinc-200 font-mono text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200"
              >
                {{ t }}
              </span>
            </div>
          </div>

          <div v-if="data.expos_seen.length" class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-calendar-days mr-1"></i> Expo terlihat
            </h3>
            <div class="space-y-1.5">
              <RouterLink
                v-for="ex in data.expos_seen"
                :key="ex"
                :to="`/expos/${ex}`"
                class="block truncate text-sm text-accent-600 hover:underline dark:text-accent-400"
              >
                {{ ex }}
              </RouterLink>
            </div>
          </div>

          <div v-if="data.enrichment_gap.length" class="card p-5">
            <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i> Enrichment Gap
            </h3>
            <p class="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
              Field berikut akan diisi saat Phase 2 paid tier aktif.
            </p>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="g in data.enrichment_gap"
                :key="g"
                class="badge bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
              >
                {{ g }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
