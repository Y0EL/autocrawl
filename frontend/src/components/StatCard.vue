<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  icon?: string
  hint?: string
  trend?: 'up' | 'down' | 'flat'
}>()
</script>

<template>
  <div class="card flex flex-col gap-2 p-5">
    <div class="flex items-start justify-between">
      <span class="text-sm font-medium text-zinc-500 dark:text-zinc-400">{{ label }}</span>
      <i
        v-if="icon"
        :class="[icon, 'text-base text-zinc-400 dark:text-zinc-500']"
      ></i>
    </div>
    <div class="flex items-baseline gap-2">
      <span class="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        {{ value }}
      </span>
      <i
        v-if="trend === 'up'"
        class="fa-solid fa-arrow-trend-up text-sm text-emerald-500"
      ></i>
      <i
        v-else-if="trend === 'down'"
        class="fa-solid fa-arrow-trend-down text-sm text-rose-500"
      ></i>
    </div>
    <span v-if="hint" class="text-xs text-zinc-500 dark:text-zinc-400">{{ hint }}</span>
  </div>
</template>
