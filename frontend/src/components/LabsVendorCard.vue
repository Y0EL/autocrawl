<script setup lang="ts">
import type { VendorCandidate } from '@/api/types'

defineProps<{
  vendor: VendorCandidate
  selected: boolean
  busyDeepen?: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle', vendorId: string): void
  (e: 'deepen', vendorId: string): void
}>()
</script>

<template>
  <button
    type="button"
    :class="[
      'group flex w-full flex-col items-stretch gap-2 border p-3 text-left transition-colors',
      selected
        ? 'border-accent-500 bg-accent-500/10 dark:bg-accent-500/20'
        : 'border-base-200 bg-white hover:border-base-300 dark:border-base-700 dark:bg-base-900 dark:hover:border-base-600',
    ]"
    @click="emit('toggle', vendor.vendor_id)"
  >
    <div class="flex items-start gap-3">
      <div class="relative">
        <input
          :checked="selected"
          type="checkbox"
          class="h-4 w-4 cursor-pointer accent-accent-500"
          tabindex="-1"
          readonly
        >
      </div>
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-base-200 bg-base-50 dark:border-base-700 dark:bg-base-800">
        <img
          v-if="vendor.logo_url"
          :src="vendor.logo_url"
          :alt="vendor.company_name"
          class="max-h-8 max-w-8 object-contain"
          referrerpolicy="no-referrer"
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        >
        <span v-else class="font-mono text-sm font-semibold text-accent-600 dark:text-accent-400">
          {{ vendor.company_name.charAt(0).toUpperCase() }}
        </span>
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate font-mono text-sm font-semibold text-base-900 dark:text-base-50">
          {{ vendor.company_name }}
        </p>
        <p class="truncate font-mono text-2xs text-base-500 dark:text-base-400">
          {{ vendor.domain || 'tanpa domain' }}
        </p>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-1.5">
      <span
        v-for="ind in vendor.industries.slice(0, 3)"
        :key="ind"
        class="border border-base-200 bg-base-50 px-1.5 py-0.5 font-mono text-2xs uppercase tracking-ops text-base-600 dark:border-base-700 dark:bg-base-800 dark:text-base-300"
      >
        {{ ind }}
      </span>
    </div>

    <div class="flex items-center justify-between gap-2 pt-1">
      <span
        v-if="vendor.has_verified_email"
        class="hud-pill hud-pill-ok"
      >
        EMAIL OK
      </span>
      <span
        v-else
        class="hud-pill hud-pill-warn"
      >
        BELUM ADA EMAIL
      </span>

      <button
        v-if="!vendor.has_verified_email"
        type="button"
        :disabled="busyDeepen"
        class="hud-btn hud-btn-ghost text-2xs"
        @click.stop="emit('deepen', vendor.vendor_id)"
      >
        {{ busyDeepen ? 'Loading..' : 'Deepen' }}
      </button>
    </div>
  </button>
</template>
