<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  current: number
  threshold: number
  loading?: boolean
}>()

const { isDark } = useTheme()

const option = computed(() => {
  const pct = props.threshold > 0 ? Math.min(100, (props.current / props.threshold) * 100) : 0
  return {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        radius: '95%',
        center: ['50%', '60%'],
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [0.4, '#ef4444'],
              [0.7, '#f59e0b'],
              [1, '#10b981'],
            ],
          },
        },
        pointer: {
          width: 4,
          length: '70%',
          itemStyle: { color: 'inherit' },
        },
        axisTick: {
          distance: -22,
          length: 6,
          lineStyle: { color: isDark.value ? '#52525b' : '#a1a1aa', width: 1 },
        },
        splitLine: {
          distance: -28,
          length: 12,
          lineStyle: { color: isDark.value ? '#71717a' : '#71717a', width: 2 },
        },
        axisLabel: {
          color: isDark.value ? '#a1a1aa' : '#52525b',
          distance: 6,
          fontSize: 11,
        },
        title: {
          offsetCenter: [0, '15%'],
          color: isDark.value ? '#a1a1aa' : '#52525b',
          fontSize: 12,
        },
        detail: {
          valueAnimation: true,
          fontSize: 32,
          fontWeight: 'bold',
          offsetCenter: [0, '-5%'],
          formatter: '{value}%',
          color: isDark.value ? '#fafafa' : '#18181b',
        },
        data: [{ value: Math.round(pct), name: `${props.current} / ${props.threshold}` }],
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-72" />
</template>
