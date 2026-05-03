<script setup lang="ts">
import type { SourceProvenance } from '@/api/types'

defineProps<{ entries: SourceProvenance[] }>()

const iconFor = (type: string): string => {
  switch (type) {
    case 'pdf':
      return 'fa-solid fa-file-pdf text-rose-500'
    case 'aggregator':
      return 'fa-solid fa-globe text-sky-500'
    case 'search':
      return 'fa-solid fa-magnifying-glass text-amber-500'
    case 'manual':
      return 'fa-solid fa-pen-to-square text-zinc-500'
    default:
      return 'fa-solid fa-circle text-zinc-500'
  }
}

const formatDate = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('id-ID', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}
</script>

<template>
  <ol class="relative space-y-4 border-l border-zinc-200 pl-6 dark:border-zinc-700">
    <li v-for="(entry, idx) in entries" :key="idx" class="relative">
      <span
        class="absolute -left-[28px] flex h-5 w-5 items-center justify-center rounded-full bg-white ring-4 ring-zinc-50 dark:bg-zinc-900 dark:ring-zinc-950"
      >
        <i :class="[iconFor(entry.type), 'text-xs']"></i>
      </span>
      <div class="card flex flex-col gap-2 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-semibold capitalize text-zinc-900 dark:text-zinc-100">
            {{ entry.type }}
          </span>
          <span
            v-if="entry.extraction_method"
            class="badge bg-zinc-100 font-mono text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
          >
            {{ entry.extraction_method }}
          </span>
          <span
            v-if="entry.page"
            class="badge bg-accent-50 text-accent-700 dark:bg-accent-500/10 dark:text-accent-300"
          >
            Halaman {{ entry.page }}
          </span>
          <span
            v-if="entry.position"
            class="badge bg-accent-50 text-accent-700 dark:bg-accent-500/10 dark:text-accent-300"
          >
            Posisi {{ entry.position }}
          </span>
          <span
            v-if="entry.confidence != null"
            class="badge bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
          >
            {{ Math.round(entry.confidence * 100) }}% yakin
          </span>
          <span class="ml-auto text-xs text-zinc-500 dark:text-zinc-400">
            {{ formatDate(entry.discovered_at) }}
          </span>
        </div>

        <a
          v-if="entry.url"
          :href="entry.url"
          target="_blank"
          rel="noopener noreferrer"
          class="break-all font-mono text-xs text-accent-600 hover:underline dark:text-accent-400"
        >
          {{ entry.url }}
        </a>

        <div
          v-if="entry.pdf_filename"
          class="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400"
        >
          <i class="fa-regular fa-file-pdf"></i>
          <span class="font-mono">{{ entry.pdf_filename }}</span>
          <span v-if="entry.pdf_sha256" class="font-mono text-zinc-400 dark:text-zinc-500">
            sha256:{{ entry.pdf_sha256.slice(0, 12) }}
          </span>
        </div>

        <p
          v-if="entry.context_snippet"
          class="rounded-md bg-zinc-50 p-2 font-mono text-xs italic text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-400"
        >
          {{ entry.context_snippet }}
        </p>
      </div>
    </li>
  </ol>
</template>
