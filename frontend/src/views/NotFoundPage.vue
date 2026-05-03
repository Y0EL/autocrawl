<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-4">
    <div class="flex h-20 w-20 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
      <i class="fa-solid fa-compass text-3xl text-zinc-400"></i>
    </div>
    <h2 class="text-2xl font-bold">Halaman tidak ditemukan</h2>
    <p class="text-sm text-zinc-500 dark:text-zinc-400">
      URL yang lo cari belum ada di console.
    </p>
    <RouterLink to="/" class="btn-primary">Kembali ke ringkasan</RouterLink>
  </div>
</template>
