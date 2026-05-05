<script setup lang="ts">
import { computed } from 'vue'
import type { FusionSuggestion, VendorCandidate } from '@/api/types'

const props = defineProps<{
  suggestion: FusionSuggestion
  vendorMap: Map<string, VendorCandidate>
}>()

const emit = defineEmits<{
  (e: 'use-suggestion', vendorIds: string[]): void
}>()

const sourceVendors = computed(() =>
  props.suggestion.source_vendor_ids
    .map((id) => props.vendorMap.get(id))
    .filter((v): v is VendorCandidate => Boolean(v)),
)

const confidencePct = computed(() => Math.round(props.suggestion.confidence * 100))
</script>

<template>
  <div class="hud-panel flex flex-col">
    <header class="hud-panel-head">
      <div class="flex items-center gap-2">
        <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
          IDE
        </span>
        <h3 class="hud-panel-title">{{ suggestion.product_name }}</h3>
      </div>
      <span class="hud-pill hud-pill-info">
        {{ confidencePct }}%
      </span>
    </header>
    <div class="hud-panel-body space-y-3">
      <p v-if="suggestion.tagline" class="font-mono text-sm text-base-700 dark:text-base-200">
        {{ suggestion.tagline }}
      </p>

      <div class="flex flex-wrap items-center gap-1.5">
        <span
          v-for="v in sourceVendors"
          :key="v.vendor_id"
          class="flex items-center gap-1 border border-base-200 bg-base-50 px-1.5 py-0.5 font-mono text-2xs text-base-700 dark:border-base-700 dark:bg-base-800 dark:text-base-200"
        >
          <span v-if="v.logo_url" class="h-3 w-3 overflow-hidden">
            <img :src="v.logo_url" :alt="v.company_name" class="h-full w-full object-contain" referrerpolicy="no-referrer">
          </span>
          {{ v.company_name }}
        </span>
        <span
          v-for="missingId in suggestion.source_vendor_ids.filter((id) => !vendorMap.get(id))"
          :key="missingId"
          class="border border-warn-300 bg-warn-50 px-1.5 py-0.5 font-mono text-2xs text-warn-700 dark:border-warn-800 dark:bg-warn-900/30 dark:text-warn-300"
        >
          ? {{ missingId.slice(0, 6) }}
        </span>
      </div>

      <p class="font-mono text-2xs text-base-500 dark:text-base-400" style="white-space: pre-line">
        {{ suggestion.rationale }}
      </p>
    </div>
    <footer class="border-t border-base-200 px-3 py-2 dark:border-base-700">
      <button
        class="hud-btn hud-btn-primary w-full"
        type="button"
        @click="emit('use-suggestion', suggestion.source_vendor_ids)"
      >
        Pakai Saran Ini
      </button>
    </footer>
  </div>
</template>
