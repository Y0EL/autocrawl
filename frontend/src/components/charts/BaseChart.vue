<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  BarChart,
  EffectScatterChart,
  GaugeChart,
  LineChart,
  PieChart,
  ScatterChart,
} from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { computed, provide } from 'vue'
import { useTheme } from '@/composables/useTheme'

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  LineChart,
  GaugeChart,
  ScatterChart,
  EffectScatterChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  DatasetComponent,
])

const { isDark } = useTheme()
const themeKey = computed(() => (isDark.value ? 'dark' : 'light'))
provide(THEME_KEY, themeKey)

defineProps<{
  option: Record<string, unknown>
  loading?: boolean
  height?: string
}>()
</script>

<template>
  <div :class="['relative w-full', height ?? 'h-72']">
    <VChart
      :option="option"
      :loading="loading"
      autoresize
      :loading-options="{
        text: 'Memuat',
        color: '#6366f1',
        textColor: isDark ? '#e4e4e7' : '#27272a',
        maskColor: isDark ? 'rgba(9, 9, 11, 0.6)' : 'rgba(255, 255, 255, 0.6)',
      }"
    />
  </div>
</template>
