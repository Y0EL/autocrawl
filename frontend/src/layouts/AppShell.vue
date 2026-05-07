<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Sidebar from '@/components/shell/Sidebar.vue'
import Topbar from '@/components/shell/Topbar.vue'
import KpiBand from '@/components/shell/KpiBand.vue'
import Footer from '@/components/shell/Footer.vue'

const route = useRoute()
/**
 * KpiBand only renders on the overview / Pusat Komando page — all the
 * editorial weight at the top is for the headline view. Other pages get
 * the topbar masthead but skip the band so their content has more
 * vertical room.
 */
const showKpi = computed(() => route.path === '/')
</script>

<template>
  <div class="flex h-full bg-paper text-ink">
    <Sidebar />
    <div class="flex flex-1 flex-col overflow-hidden">
      <Topbar />
      <KpiBand v-if="showKpi" />
      <main class="relative flex-1 overflow-y-auto bg-paper">
        <RouterView v-slot="{ Component }">
          <Transition name="paper-fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
      <Footer />
    </div>
  </div>
</template>

<style scoped>
.paper-fade-enter-active,
.paper-fade-leave-active {
  transition: opacity 160ms cubic-bezier(0.2, 0.6, 0.2, 1),
              transform 160ms cubic-bezier(0.2, 0.6, 0.2, 1);
}
.paper-fade-enter-from,
.paper-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
