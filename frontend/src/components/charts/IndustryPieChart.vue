<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: { tag: string; count: number }[]
  loading?: boolean
}>()

const { isDark } = useTheme()

const palette = ['#6366f1', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#0ea5e9', '#f97316', '#14b8a6']

const option = computed(() => ({
  backgroundColor: 'transparent',
  textStyle: { color: isDark.value ? '#e4e4e7' : '#27272a' },
  tooltip: {
    trigger: 'item',
    formatter: '{b}: <b>{c}</b> ({d}%)',
  },
  legend: {
    bottom: 0,
    icon: 'circle',
    textStyle: { color: isDark.value ? '#a1a1aa' : '#52525b' },
  },
  series: [
    {
      name: 'Industri',
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 6,
        borderColor: isDark.value ? '#18181b' : '#fafafa',
        borderWidth: 2,
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0, 0, 0, 0.3)' },
      },
      data: props.data.map((d, i) => ({
        name: d.tag,
        value: d.count,
        itemStyle: { color: palette[i % palette.length] },
      })),
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :loading="loading" height="h-80" />
</template>
