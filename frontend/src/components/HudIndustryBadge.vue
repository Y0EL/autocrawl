<script setup lang="ts">
import { computed } from 'vue'

const palette = [
  '#FFB800',
  '#22C55E',
  '#06B6D4',
  '#F59E0B',
  '#A78BFA',
  '#F472B6',
  '#34D399',
  '#FB923C',
]

const props = defineProps<{
  label: string
}>()

const color = computed(() => {
  let hash = 0
  for (const ch of props.label) {
    hash = (hash * 31 + ch.charCodeAt(0)) | 0
  }
  return palette[Math.abs(hash) % palette.length]
})
</script>

<template>
  <span
    class="hud-pill"
    :style="{
      borderColor: color + '55',
      backgroundColor: color + '15',
      color,
    }"
  >
    <span
      class="h-1.5 w-1.5 shrink-0 rounded-full"
      :style="{ backgroundColor: color }"
    />
    <span class="truncate">{{ label }}</span>
  </span>
</template>
