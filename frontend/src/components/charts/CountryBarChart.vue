<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { country: string; count: number }[]
  loading?: boolean
}>()

const { isDark } = useTheme()

const option = computed(() => {
  const sorted = [...props.data].sort((a, b) => a.count - b.count)
  return {
    backgroundColor: 'transparent',
    textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
    grid: { left: 80, right: 30, top: 20, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: isDark.value ? '#3f3f46' : '#d4d4d8' } },
      splitLine: { lineStyle: { color: isDark.value ? '#27272a' : '#f4f4f5' } },
      axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b' },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((d) => d.country),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b' },
    },
    series: [
      {
        type: 'bar',
        data: sorted.map((d) => d.count),
        barWidth: '60%',
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#6366f1' },
              { offset: 1, color: '#818cf8' },
            ],
          },
          borderRadius: [0, 4, 4, 0],
        },
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-80" />
</template>
