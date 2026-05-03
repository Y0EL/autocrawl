<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { date: string; vendors_added: number }[]
  loading?: boolean
}>()

const { isDark } = useTheme()

const option = computed(() => {
  let cumulative = 0
  const cum = props.data.map((d) => {
    cumulative += d.vendors_added
    return cumulative
  })

  return {
    backgroundColor: 'transparent',
    textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
    grid: { left: 50, right: 30, top: 50, bottom: 30 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      right: 0,
      textStyle: { color: isDark.value ? '#a1a1aa' : '#52525b' },
    },
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.date),
      axisLine: { lineStyle: { color: isDark.value ? '#3f3f46' : '#d4d4d8' } },
      axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: isDark.value ? '#27272a' : '#f4f4f5' } },
      axisLabel: { color: isDark.value ? '#a1a1aa' : '#52525b' },
    },
    series: [
      {
        name: 'Per hari',
        type: 'bar',
        data: props.data.map((d) => d.vendors_added),
        itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
        barWidth: '50%',
      },
      {
        name: 'Kumulatif',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: cum,
        lineStyle: { width: 3, color: '#10b981' },
        itemStyle: { color: '#10b981' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.4)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0)' },
            ],
          },
        },
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-80" />
</template>
