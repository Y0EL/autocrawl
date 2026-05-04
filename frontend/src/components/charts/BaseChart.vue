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
  DataZoomComponent,
  DatasetComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
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
  DataZoomComponent,
  GraphicComponent,
  MarkLineComponent,
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
        text: 'MEMUAT',
        color: '#FFB800',
        textColor: isDark ? '#E5EAF1' : '#2A3340',
        maskColor: isDark ? 'rgba(7, 9, 12, 0.7)' : 'rgba(255, 255, 255, 0.7)',
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: 11,
        fontWeight: 500,
      }"
    />
  </div>
</template>
