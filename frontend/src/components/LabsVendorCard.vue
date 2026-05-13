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
      'group flex w-full flex-col items-stretch gap-2.5 p-3 text-left transition-all',
      'rounded-[6px] border',
      selected
        ? 'border-amber bg-amber/10 shadow-[0_0_18px_rgba(255,184,64,0.18)]'
        : 'border-rule bg-surface hover:border-rule-strong hover:bg-surface-2',
    ]"
    @click="emit('toggle', vendor.vendor_id)"
  >
    <div class="flex items-start gap-3">
      <div class="relative shrink-0">
        <span
          :class="[
            'flex h-4 w-4 items-center justify-center rounded-[3px] border transition-colors',
            selected ? 'border-amber bg-amber' : 'border-ink-mute bg-surface-2',
          ]"
        >
          <FaIcon v-if="selected" :icon="['fas', 'check']" class="text-[8px] text-bg" />
        </span>
      </div>

      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-rule-strong bg-surface-2">
        <img
          v-if="vendor.logo_url"
          :src="vendor.logo_url"
          :alt="vendor.company_name"
          class="max-h-8 max-w-8 object-contain"
          referrerpolicy="no-referrer"
          @error="($event.target as HTMLImageElement).style.display = 'none'"
        >
        <span v-else class="text-[14px] font-bold text-amber">
          {{ vendor.company_name.charAt(0).toUpperCase() }}
        </span>
      </div>

      <div class="min-w-0 flex-1">
        <p class="truncate text-[13px] font-semibold text-ink">
          {{ vendor.company_name }}
        </p>
        <p class="truncate num-display text-[11px] text-ink-mute">
          {{ vendor.domain || 'tanpa domain' }}
        </p>
      </div>
    </div>

    <div v-if="vendor.industries.length" class="flex flex-wrap items-center gap-1.5">
      <span
        v-for="ind in vendor.industries.slice(0, 3)"
        :key="ind"
        class="px-1.5 py-0.5 rounded-[3px] text-[10px] font-semibold uppercase tracking-[0.10em] text-ink-2 bg-surface-2 border border-rule"
      >
        {{ ind }}
      </span>
    </div>

    <div class="flex items-center justify-between gap-2 pt-1 rule-t">
      <span
        v-if="vendor.has_verified_email"
        class="pill pill-ok text-[9.5px]"
      >
        <FaIcon :icon="['fas', 'check']" class="text-[8px]" />
        Email OK
      </span>
      <span v-else class="pill text-[9.5px]" style="border-color: rgb(var(--warn) / 0.5); color: rgb(var(--warn))">
        Belum ada email
      </span>

      <button
        v-if="!vendor.has_verified_email"
        type="button"
        :disabled="busyDeepen"
        class="text-[10px] font-semibold uppercase tracking-[0.10em] text-amber hover:text-amber-hot disabled:opacity-50 transition-colors"
        @click.stop="emit('deepen', vendor.vendor_id)"
      >
        {{ busyDeepen ? 'Loading…' : 'Deepen →' }}
      </button>
    </div>
  </button>
</template>
