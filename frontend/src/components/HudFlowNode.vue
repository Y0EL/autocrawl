<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: {
    code: string
    label: string
    description: string
    active: number
    completed: number
    failed: number
    lastEventAt: number | null
  }
}>()

const ledClass = computed(() => {
  if (props.data.failed > 0 && props.data.active === 0) return 'hud-led-crit animate-pulse-led'
  if (props.data.active > 0) return 'hud-led-warn animate-pulse-led'
  if (props.data.completed > 0) return 'hud-led-ok'
  return 'hud-led-muted'
})

const tone = computed(() => {
  if (props.data.failed > 0) return '#EF4444'
  if (props.data.active > 0) return '#FFB800'
  if (props.data.completed > 0) return '#22C55E'
  return '#5C6878'
})
</script>

<template>
  <div
    class="hud-flow-node group relative flex w-[240px] flex-col border bg-white shadow-sm transition-shadow dark:bg-base-900"
    :style="{ borderColor: tone, boxShadow: `0 0 0 1px ${tone}20` }"
  >
    <Handle type="target" :position="Position.Left" class="!h-2 !w-2 !border !border-base-400 !bg-base-100 dark:!bg-base-800" />
    <Handle type="source" :position="Position.Right" class="!h-2 !w-2 !border !border-base-400 !bg-base-100 dark:!bg-base-800" />

    <div class="flex items-center justify-between border-b border-base-200 bg-base-50 px-2 py-1 dark:border-base-700 dark:bg-base-800">
      <div class="flex items-center gap-1.5">
        <span :class="ledClass" />
        <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">
          {{ data.code }}
        </span>
      </div>
      <span class="hud-mono-num text-2xs text-base-500 dark:text-base-400">
        {{ data.active }}A
      </span>
    </div>

    <div class="flex flex-col gap-1 p-2">
      <div class="font-mono text-xs font-medium uppercase tracking-ops text-base-800 dark:text-base-100">
        {{ data.label }}
      </div>
      <div class="line-clamp-2 text-2xs text-base-500 dark:text-base-400">
        {{ data.description }}
      </div>

      <div class="mt-1 grid grid-cols-3 gap-1 border-t border-base-100 pt-1.5 dark:border-base-800">
        <div class="flex flex-col items-center">
          <span class="font-mono text-[9px] uppercase tracking-ops text-base-400 dark:text-base-500">AKTIF</span>
          <span
            class="hud-mono-num text-sm font-semibold"
            :style="{ color: data.active > 0 ? '#FFB800' : '#8F99A8' }"
          >
            {{ data.active }}
          </span>
        </div>
        <div class="flex flex-col items-center">
          <span class="font-mono text-[9px] uppercase tracking-ops text-base-400 dark:text-base-500">OK</span>
          <span
            class="hud-mono-num text-sm font-semibold"
            :style="{ color: data.completed > 0 ? '#22C55E' : '#8F99A8' }"
          >
            {{ data.completed }}
          </span>
        </div>
        <div class="flex flex-col items-center">
          <span class="font-mono text-[9px] uppercase tracking-ops text-base-400 dark:text-base-500">GAGAL</span>
          <span
            class="hud-mono-num text-sm font-semibold"
            :style="{ color: data.failed > 0 ? '#EF4444' : '#8F99A8' }"
          >
            {{ data.failed }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
