<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'

const { isDark, toggleDark } = useTheme()
</script>

<template>
  <button
    class="btn-ghost h-9 w-9 rounded-md p-0"
    :aria-label="isDark ? 'Aktifkan mode terang' : 'Aktifkan mode gelap'"
    @click="toggleDark()"
  >
    <i v-if="isDark" class="fa-regular fa-sun text-base"></i>
    <i v-else class="fa-regular fa-moon text-base"></i>
  </button>
</template>
