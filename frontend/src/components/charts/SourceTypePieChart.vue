<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { type: string; count: number }[]
  loading?: boolean
}>()

const { isDark } = useTheme()

const colorMap: Record<string, string> = {
  pdf: '#ef4444',
  aggregator: '#0ea5e9',
  search: '#f59e0b',
  manual: '#a1a1aa',
}

const option = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
  tooltip: { trigger: 'item', formatter: '{b}: <b>{c}</b> ({d}%)' },
  legend: {
    orient: 'vertical',
    right: 0,
    top: 'middle',
    icon: 'roundRect',
    textStyle: { color: isDark.value ? '#a1a1aa' : '#52525b' },
  },
  series: [
    {
      name: 'Sumber',
      type: 'pie',
      radius: ['55%', '80%'],
      center: ['40%', '50%'],
      itemStyle: {
        borderRadius: 8,
        borderColor: isDark.value ? '#18181b' : '#fafafa',
        borderWidth: 3,
      },
      label: { show: false },
      data: props.data.map((d) => ({
        name: d.type,
        value: d.count,
        itemStyle: { color: colorMap[d.type] ?? '#71717a' },
      })),
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-72" />
</template>
