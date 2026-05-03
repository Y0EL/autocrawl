<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { mode: string; count: number }[]
  loading?: boolean
}>()

const { isDark } = useTheme()

const colorMap: Record<string, string> = {
  dev: '#f59e0b',
  normal: '#10b981',
  aggressive: '#ef4444',
}

const option = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
  grid: { left: 60, right: 30, top: 30, bottom: 30 },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: {
    type: 'category',
    data: props.data.map((d) => d.mode),
    axisLine: { lineStyle: { color: isDark.value ? '#3f3f46' : '#d4d4d8' } },
    axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b', fontWeight: 'bold' },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: isDark.value ? '#27272a' : '#f4f4f5' } },
    axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b' },
  },
  series: [
    {
      type: 'bar',
      barWidth: '40%',
      data: props.data.map((d) => ({
        value: d.count,
        itemStyle: { color: colorMap[d.mode] ?? '#71717a', borderRadius: [4, 4, 0, 0] },
      })),
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-64" />
</template>
