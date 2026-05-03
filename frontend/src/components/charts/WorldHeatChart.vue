<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { country: string; count: number }[]
}>()

const { isDark } = useTheme()

const option = computed(() => {
  const sorted = [...props.data].sort((a, b) => b.count - a.count).slice(0, 30)
  const grid: { name: string; count: number; row: number; col: number }[] = []
  const cols = 6
  sorted.forEach((d, i) => {
    grid.push({ name: d.country, count: d.count, col: i % cols, row: Math.floor(i / cols) })
  })
  const max = Math.max(1, ...sorted.map((d) => d.count))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark.value ? '#27272a' : '#fff',
      borderColor: isDark.value ? '#3f3f46' : '#e4e4e7',
      textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
      formatter: (p: { data: { name: string; value: [number, number, number] } }) =>
        `<b>${p.data.name}</b><br/>${p.data.value[2]} vendor`,
    },
    grid: { left: 20, right: 20, top: 10, bottom: 10, containLabel: false },
    xAxis: { type: 'value', show: false, min: -0.5, max: cols - 0.5 },
    yAxis: { type: 'value', show: false, min: -0.5, max: Math.max(0, Math.ceil(grid.length / cols)) - 0.5, inverse: true },
    series: [
      {
        type: 'scatter',
        symbol: 'circle',
        symbolSize: (val: [number, number, number]) => 18 + (val[2] / max) * 38,
        data: grid.map((g) => ({
          name: g.name,
          value: [g.col, g.row, g.count],
          itemStyle: {
            color: {
              type: 'radial',
              x: 0.5,
              y: 0.5,
              r: 0.5,
              colorStops: [
                { offset: 0, color: '#a5b4fc' },
                { offset: 1, color: '#6366f1' },
              ],
            },
            shadowBlur: 12,
            shadowColor: 'rgba(99, 102, 241, 0.4)',
          },
          label: {
            show: true,
            formatter: (p: { data: { value: [number, number, number] } }) =>
              `${p.data.value[2]}`,
            color: isDark.value ? '#fafafa' : '#18181b',
            fontWeight: 'bold',
            fontSize: 10,
          },
        })),
      },
      {
        type: 'scatter',
        symbol: 'rect',
        symbolSize: 0,
        data: grid.map((g) => ({
          name: g.name,
          value: [g.col, g.row + 0.45, g.count],
          label: {
            show: true,
            formatter: g.name.length > 16 ? g.name.slice(0, 14) + '..' : g.name,
            color: isDark.value ? '#a1a1aa' : '#52525b',
            fontSize: 10,
          },
        })),
        silent: true,
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" height="h-72" />
</template>
