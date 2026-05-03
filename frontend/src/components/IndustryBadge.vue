<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  tag: string
}>()

const palette: Record<string, string> = {
  defense: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400',
  cybersecurity: 'bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400',
  law_enforcement: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
  surveillance: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
  border_control: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
  critical_infra: 'bg-orange-100 text-orange-700 dark:bg-orange-500/10 dark:text-orange-400',
  aerospace: 'bg-sky-100 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400',
  dual_use: 'bg-teal-100 text-teal-700 dark:bg-teal-500/10 dark:text-teal-400',
}

const cls = computed(
  () => palette[props.tag] ?? 'bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300',
)
</script>

<template>
  <span :class="['badge', cls]">{{ tag }}</span>
</template>
