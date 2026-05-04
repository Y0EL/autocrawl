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
    :toast-options="{
      style: {
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: '12px',
        borderRadius: '0',
      },
    }"
  />
</template>
