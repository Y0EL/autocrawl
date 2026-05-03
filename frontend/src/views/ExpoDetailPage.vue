<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'

const props = defineProps<{ expoId: string }>()

const { data, isLoading, isError } = useQuery({
  queryKey: ['expo', () => props.expoId],
  queryFn: () => api.expo(props.expoId),
})
</script>

<template>
  <div>
    <RouterLink
      to="/expos"
      class="mb-4 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
    >
      <i class="fa-solid fa-arrow-left text-xs"></i>
      Kembali ke daftar expo
    </RouterLink>

    <div v-if="isLoading" class="card animate-pulse p-8">
      <div class="h-6 w-1/3 rounded bg-zinc-200 dark:bg-zinc-800"></div>
    </div>

    <div v-else-if="isError" class="card p-8 text-center text-rose-500">Expo tidak ditemukan.</div>

    <div v-else-if="data" class="space-y-6">
      <div class="card p-6">
        <h2 class="text-2xl font-bold tracking-tight">{{ data.name }}</h2>
        <p class="mt-1 font-mono text-xs text-zinc-500 dark:text-zinc-400">{{ data.expo_id }}</p>

        <dl class="mt-4 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <div>
            <dt class="text-zinc-500 dark:text-zinc-400">Negara</dt>
            <dd class="font-medium">{{ data.country ?? '-' }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500 dark:text-zinc-400">Lokasi</dt>
            <dd class="font-medium">{{ data.location ?? '-' }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500 dark:text-zinc-400">Tanggal mulai</dt>
            <dd class="font-medium">{{ data.start_date ?? '-' }}</dd>
          </div>
          <div>
            <dt class="text-zinc-500 dark:text-zinc-400">Tanggal selesai</dt>
            <dd class="font-medium">{{ data.end_date ?? '-' }}</dd>
          </div>
        </dl>

        <div class="mt-4 flex flex-wrap gap-2">
          <a
            v-if="data.aggregator_url"
            :href="data.aggregator_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-ghost h-8 px-3 text-xs"
          >
            <i class="fa-solid fa-globe"></i> Halaman aggregator
          </a>
          <a
            v-if="data.official_url"
            :href="data.official_url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-ghost h-8 px-3 text-xs"
          >
            <i class="fa-solid fa-link"></i> Situs resmi
          </a>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <div class="card p-5">
          <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            <i class="fa-solid fa-building mr-1"></i> Vendor Terkoleksi
            <span class="ml-2 tabular-nums">({{ data.vendor_domains?.length ?? 0 }})</span>
          </h3>
          <div v-if="data.vendor_domains?.length" class="space-y-1">
            <RouterLink
              v-for="d in data.vendor_domains"
              :key="d"
              :to="`/vendors/${d}`"
              class="flex items-center justify-between rounded-md px-3 py-2 font-mono text-sm text-accent-600 hover:bg-zinc-50 dark:text-accent-400 dark:hover:bg-zinc-800/40"
            >
              <span>{{ d }}</span>
              <i class="fa-solid fa-chevron-right text-xs"></i>
            </RouterLink>
          </div>
          <p v-else class="text-sm text-zinc-500 dark:text-zinc-400">Belum ada vendor terkoleksi.</p>
        </div>

        <div class="card p-5">
          <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            <i class="fa-solid fa-file-pdf mr-1"></i> Brosur PDF
            <span class="ml-2 tabular-nums">({{ data.pdf_brochure_urls?.length ?? 0 }})</span>
          </h3>
          <div v-if="data.pdf_brochure_urls?.length" class="space-y-1">
            <a
              v-for="url in data.pdf_brochure_urls"
              :key="url"
              :href="url"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center gap-2 rounded-md px-3 py-2 font-mono text-xs text-accent-600 hover:bg-zinc-50 dark:text-accent-400 dark:hover:bg-zinc-800/40"
            >
              <i class="fa-solid fa-file-pdf shrink-0"></i>
              <span class="truncate">{{ url }}</span>
            </a>
          </div>
          <p v-else class="text-sm text-zinc-500 dark:text-zinc-400">Tidak ada brosur PDF.</p>
        </div>
      </div>
    </div>
  </div>
</template>
