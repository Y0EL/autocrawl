<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: number[]
  labels?: string[]
  color?: string
  type?: 'bar' | 'line'
}>()

const { isDark } = useTheme()

const option = computed(() => {
  const color = props.color ?? '#6366f1'
  const isBar = (props.type ?? 'bar') === 'bar'
  return {
    backgroundColor: 'transparent',
    grid: { left: 0, right: 0, top: 4, bottom: 0 },
    tooltip: {
      trigger: 'axis',
      formatter: (params: { dataIndex: number; value: number }[]) => {
        const p = params[0]
        const label = props.labels?.[p.dataIndex] ?? p.dataIndex
        return `<span style="font-size:11px">${label}: <b>${p.value}</b></span>`
      },
      backgroundColor: isDark.value ? '#27272a' : '#fff',
      borderColor: isDark.value ? '#3f3f46' : '#e4e4e7',
      textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      data: props.labels ?? props.data.map((_, i) => i),
      show: false,
    },
    yAxis: { type: 'value', show: false },
    series: [
      isBar
        ? {
            type: 'bar',
            data: props.data,
            barWidth: '60%',
            itemStyle: { color, borderRadius: [2, 2, 0, 0] },
          }
        : {
            type: 'line',
            data: props.data,
            symbol: 'none',
            smooth: true,
            lineStyle: { color, width: 2 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: color + '66' },
                  { offset: 1, color: color + '00' },
                ],
              },
            },
          },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" height="h-16" />
</template>
