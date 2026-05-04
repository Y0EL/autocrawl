<script setup lang="ts">
import HudOpsStatusBar from '@/components/HudOpsStatusBar.vue'
import HudOpsCurrentActivity from '@/components/HudOpsCurrentActivity.vue'
import HudOpsThroughput from '@/components/HudOpsThroughput.vue'
import HudOpsTimeline from '@/components/HudOpsTimeline.vue'
import HudOpsErrorInbox from '@/components/HudOpsErrorInbox.vue'
</script>

<template>
  <div class="flex flex-col gap-3 p-3">
    <div class="flex items-center justify-between">
      <span class="font-mono text-xs uppercase tracking-ops text-base-400 dark:text-base-500">
        OPS-07 / KONSOL OPERASI LIVE
      </span>
      <span class="font-mono text-2xs uppercase tracking-ops text-accent-600 dark:text-accent-300">
        HUMAN READABLE
      </span>
    </div>

    <HudOpsStatusBar />

    <div class="grid grid-cols-1 gap-3 lg:grid-cols-12">
      <div class="lg:col-span-8">
        <HudOpsCurrentActivity />
      </div>
      <div class="lg:col-span-4">
        <HudOpsThroughput />
      </div>
    </div>

    <div class="grid grid-cols-1 gap-3 lg:grid-cols-12">
      <div class="lg:col-span-7">
        <HudOpsTimeline />
      </div>
      <div class="lg:col-span-5">
        <HudOpsErrorInbox />
      </div>
    </div>
  </div>
</template>
