<script setup lang="ts">
import SparklineChart from './charts/SparklineChart.vue'

defineProps<{
  label: string
  hint?: string
  value: string | number
  emphasis?: string
  series?: number[]
  seriesLabels?: string[]
  color?: string
  type?: 'bar' | 'line'
}>()
</script>

<template>
  <div
    class="card flex h-full flex-col gap-2 border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-zinc-700"
  >
    <div>
      <div class="flex items-baseline gap-2 text-zinc-100">
        <span class="text-base font-semibold">{{ label }}</span>
        <span v-if="emphasis" class="text-sm font-mono text-zinc-500">{{ emphasis }}</span>
      </div>
      <p v-if="hint" class="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{{ hint }}</p>
    </div>
    <div class="flex items-end justify-between gap-3">
      <span
        class="text-3xl font-bold tabular-nums leading-none tracking-tight"
        :style="{ color: color ?? undefined }"
      >
        {{ value }}
      </span>
      <div v-if="series && series.length" class="h-12 w-32 shrink-0">
        <SparklineChart :data="series" :labels="seriesLabels" :color="color" :type="type" />
      </div>
    </div>
  </div>
</template>
