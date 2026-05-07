<script setup lang="ts">
import { Toaster } from 'vue-sonner'
import AppShell from '@/layouts/AppShell.vue'
import { useTheme } from '@/composables/useTheme'

const { isDark } = useTheme()
</script>

<template>
  <AppShell />
  <Toaster
    :theme="isDark ? 'dark' : 'light'"
    position="top-right"
    rich-colors
    close-button
    :offset="16"
    :toast-options="{
      style: {
        fontFamily: '\'JetBrains Mono Variable\', \'JetBrains Mono\', monospace',
        fontSize: '12px',
        borderRadius: '0',
        border: '1px solid rgba(20,18,16,0.18)',
        background: 'rgb(244,239,230)',
        color: 'rgb(20,18,16)',
        boxShadow: '0 8px 28px rgba(0,0,0,0.10)',
      },
    }"
  />
</template>
