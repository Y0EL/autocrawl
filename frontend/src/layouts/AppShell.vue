<script setup lang="ts">
import { RouterView } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import Topbar from '@/components/Topbar.vue'
</script>

<template>
  <div class="relative flex h-full">
    <Sidebar />
    <div class="flex flex-1 flex-col overflow-hidden">
      <Topbar />
      <main class="relative flex-1 overflow-y-auto bg-base-50 dark:bg-base-950">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
        <footer
          class="sticky bottom-0 z-0 flex h-6 items-center justify-between border-t border-base-200 bg-white px-3 font-mono text-2xs uppercase tracking-ops text-base-400 dark:border-base-700 dark:bg-base-900 dark:text-base-500"
        >
          <span>autocrawl ops console</span>
          <div class="flex items-center gap-3">
            <span>BUILD 0.2</span>
            <span>OPS PROFILE: DEFCON-IDLE</span>
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.12s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
