<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  score: number
  showLabel?: boolean
}>()

const pct = computed(() => Math.round(Math.max(0, Math.min(1, props.score)) * 100))

const colour = computed(() => {
  if (pct.value >= 75) return 'bg-emerald-500'
  if (pct.value >= 50) return 'bg-amber-500'
  if (pct.value >= 25) return 'bg-orange-500'
  return 'bg-rose-500'
})

const textColour = computed(() => {
  if (pct.value >= 75) return 'text-emerald-700 dark:text-emerald-400'
  if (pct.value >= 50) return 'text-amber-700 dark:text-amber-400'
  if (pct.value >= 25) return 'text-orange-700 dark:text-orange-400'
  return 'text-rose-700 dark:text-rose-400'
})
</script>

<template>
  <div class="flex items-center gap-2">
    <div class="h-2 flex-1 rounded-full bg-zinc-200 dark:bg-zinc-800">
      <div
        :class="[colour, 'h-full rounded-full transition-all']"
        :style="{ width: `${pct}%` }"
      ></div>
    </div>
    <span v-if="showLabel" :class="[textColour, 'shrink-0 text-xs font-semibold tabular-nums']">
      {{ pct }}%
    </span>
  </div>
</template>
