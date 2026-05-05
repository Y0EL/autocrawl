<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import type { Fusion, FusionEmailDraft, FusionListItem } from '@/api/types'

const props = defineProps<{
  fusion: Fusion | FusionListItem
  compact?: boolean
}>()

const emit = defineEmits<{
  (e: 'open-detail', fusionId: string): void
}>()

const expanded = ref<Set<number>>(new Set())

function toggleExpand(id: number) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
  expanded.value = new Set(expanded.value)
}

async function copyDraft(draft: FusionEmailDraft) {
  const text = `Subject: ${draft.subject}\n\n${draft.body}`
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Draft tersalin')
    try {
      await api.labs.markCopied(props.fusion.fusion_id, draft.id)
    } catch (e) {
      // analytics non-fatal
    }
  } catch (e) {
    toast.error('Gagal salin ke clipboard')
  }
}
</script>

<template>
  <div v-if="compact" class="hud-panel cursor-pointer transition-colors hover:border-accent-500" @click="emit('open-detail', fusion.fusion_id)">
    <div class="hud-panel-body flex gap-3">
      <div class="h-20 w-32 shrink-0 overflow-hidden border border-base-200 bg-base-50 dark:border-base-700 dark:bg-base-800">
        <img v-if="fusion.image_url" :src="fusion.image_url" alt="" class="h-full w-full object-cover">
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate font-mono text-sm font-semibold text-base-900 dark:text-base-50">{{ fusion.name }}</p>
        <p v-if="fusion.tagline" class="truncate font-mono text-2xs text-base-500 dark:text-base-400">{{ fusion.tagline }}</p>
        <p class="mt-1 font-mono text-2xs text-base-400 dark:text-base-500">
          {{ ('source_vendor_count' in fusion ? fusion.source_vendor_count : (fusion as Fusion).source_vendor_ids?.length) ?? 0 }} vendor source
        </p>
      </div>
    </div>
  </div>

  <div v-else-if="'description' in fusion" class="space-y-4">
    <div class="hud-panel">
      <div class="hud-panel-body space-y-3">
        <div v-if="fusion.image_url" class="overflow-hidden border border-base-200 dark:border-base-700">
          <img :src="fusion.image_url" alt="" class="w-full">
        </div>
        <h2 class="font-mono text-2xl font-semibold text-base-900 dark:text-base-50">{{ fusion.name }}</h2>
        <p v-if="fusion.tagline" class="font-mono text-base text-accent-700 dark:text-accent-400">{{ fusion.tagline }}</p>
        <p v-if="fusion.description" class="font-mono text-sm text-base-700 dark:text-base-200" style="white-space: pre-line">{{ fusion.description }}</p>

        <div class="flex flex-wrap items-center gap-1.5">
          <span
            v-for="ind in fusion.industries"
            :key="ind"
            class="border border-base-200 bg-base-50 px-1.5 py-0.5 font-mono text-2xs uppercase tracking-ops text-base-600 dark:border-base-700 dark:bg-base-800 dark:text-base-300"
          >
            {{ ind }}
          </span>
        </div>

        <p v-if="fusion.rationale" class="border-l-2 border-accent-500 pl-3 font-mono text-2xs italic text-base-500 dark:text-base-400" style="white-space: pre-line">
          {{ fusion.rationale }}
        </p>
      </div>
    </div>

    <div v-if="fusion.source_vendors?.length" class="hud-panel">
      <header class="hud-panel-head">
        <h3 class="hud-panel-title">Source Vendors</h3>
      </header>
      <div class="hud-panel-body grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div
          v-for="v in fusion.source_vendors"
          :key="v.vendor_id"
          class="flex items-center gap-3 border border-base-200 p-2 dark:border-base-700"
        >
          <div class="h-8 w-8 shrink-0 border border-base-200 bg-base-50 dark:border-base-700 dark:bg-base-800">
            <img v-if="v.logo_url" :src="v.logo_url" :alt="v.company_name" class="h-full w-full object-contain" referrerpolicy="no-referrer">
          </div>
          <div class="min-w-0">
            <p class="truncate font-mono text-sm text-base-900 dark:text-base-50">{{ v.company_name }}</p>
            <p class="truncate font-mono text-2xs text-base-500 dark:text-base-400">{{ v.domain }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="fusion.drafts?.length" class="hud-panel">
      <header class="hud-panel-head">
        <h3 class="hud-panel-title">Email Drafts ({{ fusion.drafts.length }})</h3>
      </header>
      <div class="hud-panel-body space-y-2">
        <div
          v-for="d in fusion.drafts"
          :key="d.id"
          class="border border-base-200 dark:border-base-700"
        >
          <button
            class="flex w-full items-center justify-between gap-3 bg-base-50 p-2 text-left transition-colors hover:bg-base-100 dark:bg-base-800 dark:hover:bg-base-700"
            type="button"
            @click="toggleExpand(d.id)"
          >
            <div class="min-w-0">
              <p class="truncate font-mono text-sm text-base-900 dark:text-base-50">{{ d.vendor_name || d.vendor_id }}</p>
              <p class="truncate font-mono text-2xs text-base-500 dark:text-base-400">{{ d.to_email }} - {{ d.subject }}</p>
            </div>
            <span class="font-mono text-2xs text-base-400">{{ expanded.has(d.id) ? '-' : '+' }}</span>
          </button>
          <div v-if="expanded.has(d.id)" class="space-y-2 border-t border-base-200 p-3 dark:border-base-700">
            <p class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">Subject</p>
            <p class="font-mono text-sm text-base-900 dark:text-base-50">{{ d.subject }}</p>
            <p class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">Body</p>
            <pre class="whitespace-pre-wrap break-words font-mono text-sm text-base-700 dark:text-base-200">{{ d.body }}</pre>
            <div class="flex justify-end">
              <button class="hud-btn hud-btn-primary" type="button" @click="copyDraft(d)">
                Salin
              </button>
            </div>
            <p v-if="d.copied_at" class="font-mono text-2xs text-base-400 dark:text-base-500">
              Pernah disalin: {{ d.copied_at }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
