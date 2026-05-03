<script setup lang="ts">
import { computed } from 'vue'
import { useApiHealth } from '@/composables/useApiHealth'

const { status, dbStatus } = useApiHealth()

const meta = computed(() => {
  if (status.value === 'down') {
    return {
      label: 'Backend offline',
      cls: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400',
      dot: 'bg-rose-500',
    }
  }
  if (status.value === 'degraded' || dbStatus.value !== 'ok') {
    return {
      label: 'Degraded',
      cls: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
      dot: 'bg-amber-500',
    }
  }
  return {
    label: 'Backend siap',
    cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
    dot: 'bg-emerald-500',
  }
})
</script>

<template>
  <span :class="['badge', meta.cls]">
    <span :class="[meta.dot, 'h-1.5 w-1.5 rounded-full']"></span>
    {{ meta.label }}
  </span>
</template>
