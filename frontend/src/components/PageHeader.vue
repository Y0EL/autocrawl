<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="mb-6 flex items-end justify-between gap-4">
    <div>
      <h2 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        {{ title }}
      </h2>
      <p v-if="subtitle" class="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{{ subtitle }}</p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
