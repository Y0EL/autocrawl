<script setup lang="ts">
defineProps<{
  icon?: string
  title: string
  hint?: string
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-zinc-300 bg-white p-12 text-center dark:border-zinc-700 dark:bg-zinc-900"
  >
    <i :class="[icon ?? 'fa-regular fa-folder-open', 'text-3xl text-zinc-400 dark:text-zinc-600']"></i>
    <h3 class="text-base font-semibold text-zinc-900 dark:text-zinc-100">{{ title }}</h3>
    <p v-if="hint" class="max-w-md text-sm text-zinc-500 dark:text-zinc-400">{{ hint }}</p>
  </div>
</template>
