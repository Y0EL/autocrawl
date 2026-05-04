<script setup lang="ts">
import { useRoute, RouterLink } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-6 p-8">
    <div class="flex flex-col items-center gap-3">
      <div class="flex h-24 w-24 items-center justify-center border-2 border-crit-500 bg-crit-500/10">
        <FaIcon :icon="['fas', 'triangle-exclamation']" class="text-3xl text-crit-500" />
      </div>
      <span class="font-mono text-2xs uppercase tracking-ops text-crit-600 dark:text-crit-400">
        ERR / 404
      </span>
    </div>

    <div class="flex flex-col items-center gap-2 text-center">
      <h2 class="font-mono text-2xl font-semibold uppercase tracking-ops text-base-800 dark:text-base-100">
        TARGET NOT FOUND
      </h2>
      <p class="hud-mono-num text-xs text-base-500 dark:text-base-400">
        PATH: {{ route.fullPath }}
      </p>
      <p class="max-w-md text-sm text-base-600 dark:text-base-300">
        Rute yang anda akses tidak terdaftar di OPS console. Periksa URL atau kembali ke pusat komando.
      </p>
    </div>

    <RouterLink to="/" class="hud-btn-primary h-9">
      <FaIcon :icon="['fas', 'gauge-high']" class="text-2xs" />
      <span>KEMBALI KE PUSAT KOMANDO</span>
    </RouterLink>
  </div>
</template>
